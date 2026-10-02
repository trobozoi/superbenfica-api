"""Regras de negócio de pedidos e separação.

Cada operação bloqueia o pedido com ``select_for_update`` para que duas
pessoas não alterem o mesmo pedido ao mesmo tempo. Ao final, os eventos são
publicados no WebSocket da filial e do cliente (após o commit).
"""

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import APIException

from apps.clientes.models import Cliente
from apps.core.realtime import notificar_loja, notificar_usuario
from apps.estoque.services import baixar_itens, devolver_itens
from apps.filiais.models import Loja
from apps.pedidos.models import ItemPedido, Pedido, Separacao, StatusPedido, StatusSeparacao
from apps.produtos.models import Produto

EVENTO_PEDIDO_CRIADO = "pedido.criado"
EVENTO_PEDIDO_ATUALIZADO = "pedido.atualizado"


class TransicaoInvalidaError(APIException):
    """Mudança de status não permitida pelo fluxo do pedido (HTTP 409)."""

    status_code = status.HTTP_409_CONFLICT
    default_detail = "Mudança de status não permitida."
    default_code = "transicao_invalida"


@dataclass(frozen=True)
class ItemSolicitado:
    """Produto e quantidade pedidos pelo cliente."""

    produto: Produto
    quantidade: int


def _notificar(pedido: Pedido, evento: str) -> None:
    """Publica o evento do pedido para a filial e para o cliente."""
    dados: dict[str, Any] = {"pedido_id": pedido.pk, "codigo": pedido.codigo, "status": pedido.status}
    notificar_loja(pedido.loja_id, evento, dados)
    if pedido.cliente.usuario_id:
        notificar_usuario(pedido.cliente.usuario_id, evento, dados)


def _bloquear_pedido(pedido_id: int) -> Pedido:
    """Obtém o pedido com bloqueio de linha."""
    return Pedido.objects.select_for_update(of=("self",)).select_related("cliente").get(pk=pedido_id)


def _mudar_status(pedido: Pedido, novo_status: str) -> None:
    """Valida e grava a transição de status."""
    if not pedido.pode_mudar_para(novo_status):
        raise TransicaoInvalidaError(f"Pedido {pedido.codigo} não pode passar de {pedido.status} para {novo_status}.")
    pedido.status = novo_status
    pedido.save(update_fields=["status", "data_atualizacao"])


@transaction.atomic
def criar_pedido(
    *,
    cliente: Cliente,
    loja: Loja,
    itens: Iterable[ItemSolicitado],
    observacao: str = "",
) -> Pedido:
    """Cria o pedido baixando o estoque da filial.

    Itens repetidos do mesmo produto são somados. O preço unitário é o preço
    atual do produto (congelado no item).

    Raises:
        EstoqueInsuficienteError / ProdutoIndisponivelError: vindos do estoque.
    """
    quantidades: Counter[int] = Counter()
    for item in itens:
        quantidades[item.produto.pk] += item.quantidade
    estoques = baixar_itens(loja.pk, dict(quantidades))
    pedido = Pedido.objects.create(cliente=cliente, loja=loja, observacao=observacao)
    ItemPedido.objects.bulk_create(
        ItemPedido(
            pedido=pedido,
            produto=estoques[produto_id].produto,
            quantidade=quantidade,
            preco_unitario=estoques[produto_id].produto.preco,
        )
        for produto_id, quantidade in quantidades.items()
    )
    _notificar(pedido, EVENTO_PEDIDO_CRIADO)
    return pedido


@transaction.atomic
def cancelar_pedido(pedido_id: int) -> Pedido:
    """Cancela o pedido, devolve o estoque e encerra separações em andamento."""
    pedido = _bloquear_pedido(pedido_id)
    _mudar_status(pedido, StatusPedido.CANCELADO)
    devolver_itens(pedido.loja_id, dict(pedido.itens.values_list("produto_id", "quantidade")))
    pedido.separacoes.filter(status=StatusSeparacao.EM_ANDAMENTO).update(
        status=StatusSeparacao.CANCELADA, data_conclusao=timezone.now()
    )
    _notificar(pedido, EVENTO_PEDIDO_ATUALIZADO)
    return pedido


@transaction.atomic
def iniciar_separacao(pedido_id: int, separador: Any) -> Separacao:
    """Coloca o pedido em separação e registra o responsável."""
    pedido = _bloquear_pedido(pedido_id)
    _mudar_status(pedido, StatusPedido.EM_SEPARACAO)
    separacao = Separacao.objects.create(pedido=pedido, usuario=separador)
    _notificar(pedido, EVENTO_PEDIDO_ATUALIZADO)
    return separacao


@transaction.atomic
def concluir_separacao(separacao_id: int) -> Separacao:
    """Conclui a separação e marca o pedido como separado."""
    separacao = Separacao.objects.select_for_update().get(pk=separacao_id)
    if separacao.status != StatusSeparacao.EM_ANDAMENTO:
        raise TransicaoInvalidaError("Esta separação não está em andamento.")
    pedido = _bloquear_pedido(separacao.pedido_id)
    _mudar_status(pedido, StatusPedido.SEPARADO)
    separacao.status = StatusSeparacao.CONCLUIDA
    separacao.data_conclusao = timezone.now()
    separacao.save(update_fields=["status", "data_conclusao"])
    _notificar(pedido, EVENTO_PEDIDO_ATUALIZADO)
    return separacao


@transaction.atomic
def finalizar_pedido(pedido_id: int) -> Pedido:
    """Finaliza (entrega/pagamento) um pedido já separado."""
    pedido = _bloquear_pedido(pedido_id)
    _mudar_status(pedido, StatusPedido.FINALIZADO)
    _notificar(pedido, EVENTO_PEDIDO_ATUALIZADO)
    return pedido

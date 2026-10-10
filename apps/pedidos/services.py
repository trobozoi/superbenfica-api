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
from rest_framework.exceptions import APIException, ValidationError

from apps.clientes.models import Cliente, EnderecoCliente
from apps.core.realtime import notificar_loja, notificar_usuario
from apps.estoque.services import baixar_itens, devolver_itens
from apps.filiais.models import Loja
from apps.pagamentos.models import FormaPagamento
from apps.pedidos.models import ItemPedido, Pedido, Separacao, StatusPedido, StatusSeparacao, TipoEntrega
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
    dados: dict[str, Any] = {
        "pedido_id": pedido.pk,
        "codigo": pedido.codigo,
        "status": pedido.status,
        "tipo_entrega": pedido.tipo_entrega,
    }
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


def formatar_endereco(endereco: EnderecoCliente) -> str:
    """Endereço em uma linha, como é gravado no pedido."""
    complemento = f" ({endereco.complemento})" if endereco.complemento else ""
    return (
        f"{endereco.endereco}, {endereco.numero}{complemento} - {endereco.bairro}, "
        f"{endereco.cidade}/{endereco.estado} - CEP {endereco.cep}"
    )


@transaction.atomic
def criar_pedido(
    *,
    cliente: Cliente,
    loja: Loja,
    itens: Iterable[ItemSolicitado],
    forma_pagamento: FormaPagamento,
    observacao: str = "",
    tipo_entrega: str = TipoEntrega.RETIRADA,
    endereco: EnderecoCliente | None = None,
) -> Pedido:
    """Cria o pedido baixando o estoque da filial.

    Itens repetidos do mesmo produto são somados. O preço unitário é o preço
    atual do produto (congelado no item). Na entrega em domicílio, o endereço
    é copiado para o pedido (o serializer garante que pertence ao cliente).

    Raises:
        EstoqueInsuficienteError / ProdutoIndisponivelError: vindos do estoque.
    """
    quantidades: Counter[int] = Counter()
    for item in itens:
        quantidades[item.produto.pk] += item.quantidade
    estoques = baixar_itens(loja.pk, dict(quantidades))
    domicilio = tipo_entrega == TipoEntrega.DOMICILIO
    if domicilio and endereco is None:
        raise ValidationError({"endereco": "Informe o endereço de entrega."})
    pedido = Pedido.objects.create(
        cliente=cliente,
        loja=loja,
        forma_pagamento=forma_pagamento,
        observacao=observacao,
        tipo_entrega=tipo_entrega,
        endereco_entrega=formatar_endereco(endereco) if domicilio and endereco else "",
    )
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


def _bloquear_separacao_ativa(separacao_id: int) -> Separacao:
    """Obtém a separação com bloqueio de linha, exigindo que esteja em andamento."""
    separacao = Separacao.objects.select_for_update().get(pk=separacao_id)
    if separacao.status != StatusSeparacao.EM_ANDAMENTO:
        raise TransicaoInvalidaError("Esta separação não está em andamento.")
    return separacao


@transaction.atomic
def marcar_item(separacao_id: int, item_id: int, separado: bool) -> ItemPedido:
    """Marca (ou desmarca) um item do pedido no checklist da separação em andamento."""
    separacao = _bloquear_separacao_ativa(separacao_id)
    pedido = _bloquear_pedido(separacao.pedido_id)
    item = pedido.itens.select_related("produto").filter(pk=item_id).first()
    if item is None:
        raise ValidationError({"item": "Este item não pertence ao pedido."})
    if item.separado != separado:
        item.separado = separado
        item.save(update_fields=["separado"])
        _notificar(pedido, EVENTO_PEDIDO_ATUALIZADO)
    return item


@transaction.atomic
def concluir_separacao(separacao_id: int) -> Separacao:
    """Conclui a separação e marca o pedido como separado."""
    separacao = _bloquear_separacao_ativa(separacao_id)
    pedido = _bloquear_pedido(separacao.pedido_id)
    _mudar_status(pedido, StatusPedido.SEPARADO)
    separacao.status = StatusSeparacao.CONCLUIDA
    separacao.data_conclusao = timezone.now()
    separacao.save(update_fields=["status", "data_conclusao"])
    _notificar(pedido, EVENTO_PEDIDO_ATUALIZADO)
    return separacao


@transaction.atomic
def despachar_pedido(pedido_id: int) -> Pedido:
    """Marca que o pedido separado de entrega em domicílio saiu para entrega."""
    pedido = _bloquear_pedido(pedido_id)
    _mudar_status(pedido, StatusPedido.SAIU_PARA_ENTREGA)
    _notificar(pedido, EVENTO_PEDIDO_ATUALIZADO)
    return pedido


@transaction.atomic
def finalizar_pedido(pedido_id: int) -> Pedido:
    """Finaliza um pedido separado (retirada) ou que saiu para entrega (domicílio)."""
    pedido = _bloquear_pedido(pedido_id)
    _mudar_status(pedido, StatusPedido.FINALIZADO)
    _notificar(pedido, EVENTO_PEDIDO_ATUALIZADO)
    return pedido

"""Regras de negócio de movimentação de estoque.

Todas as funções que alteram saldo bloqueiam as linhas envolvidas com
``select_for_update`` dentro de ``transaction.atomic``, evitando que duas
vendas simultâneas consumam o mesmo saldo.
"""

from django.db import transaction
from django.utils import timezone

from apps.core.realtime import notificar_loja
from apps.estoque.exceptions import EstoqueInsuficienteError, ProdutoIndisponivelError
from apps.estoque.models import EstoqueLocal

EVENTO_ESTOQUE_ATUALIZADO = "estoque.atualizado"


def _notificar_saldos(estoques: list[EstoqueLocal]) -> None:
    """Publica os novos saldos no canal WebSocket de cada filial."""
    for estoque in estoques:
        notificar_loja(
            estoque.loja_id,
            EVENTO_ESTOQUE_ATUALIZADO,
            {
                "estoque_id": estoque.pk,
                "produto_id": estoque.produto_id,
                "quantidade": estoque.quantidade,
                "abaixo_do_minimo": estoque.abaixo_do_minimo,
            },
        )


@transaction.atomic
def ajustar_estoque(estoque_id: int, delta: int) -> EstoqueLocal:
    """Soma ``delta`` (positivo ou negativo) ao saldo de um estoque.

    Raises:
        EstoqueInsuficienteError: se o saldo final ficaria negativo.
    """
    estoque = EstoqueLocal.objects.select_for_update().get(pk=estoque_id)
    novo_saldo = estoque.quantidade + delta
    if novo_saldo < 0:
        raise EstoqueInsuficienteError(f"Saldo atual ({estoque.quantidade}) insuficiente para baixar {-delta}.")
    estoque.quantidade = novo_saldo
    estoque.save(update_fields=["quantidade", "data_atualizacao"])
    _notificar_saldos([estoque])
    return estoque


def _salvar_saldos(estoques: list[EstoqueLocal]) -> None:
    """Grava os novos saldos em lote e notifica as filiais.

    ``bulk_update`` não aciona ``auto_now``, por isso a data é definida aqui.
    """
    agora = timezone.now()
    for estoque in estoques:
        estoque.data_atualizacao = agora
    EstoqueLocal.objects.bulk_update(estoques, ["quantidade", "data_atualizacao"])
    _notificar_saldos(estoques)


def _bloquear_estoques(loja_id: int, produto_ids: list[int]) -> dict[int, EstoqueLocal]:
    """Bloqueia e retorna os estoques da filial indexados por ``produto_id``."""
    estoques = (
        EstoqueLocal.objects.select_for_update(of=("self",))
        .select_related("produto")
        .filter(loja_id=loja_id, produto_id__in=produto_ids)
        .order_by("produto_id")
    )
    return {estoque.produto_id: estoque for estoque in estoques}


@transaction.atomic
def baixar_itens(loja_id: int, quantidades: dict[int, int]) -> dict[int, EstoqueLocal]:
    """Baixa do estoque da filial as quantidades por produto (venda/pedido).

    Args:
        loja_id: filial onde o pedido foi feito.
        quantidades: mapa ``produto_id -> quantidade``.

    Returns:
        Os estoques atualizados, indexados por ``produto_id``.

    Raises:
        ProdutoIndisponivelError: produto inativo ou sem estoque na filial.
        EstoqueInsuficienteError: saldo menor que o solicitado.
    """
    estoques = _bloquear_estoques(loja_id, list(quantidades))
    for produto_id, quantidade in quantidades.items():
        estoque = estoques.get(produto_id)
        if estoque is None or not estoque.produto.ativo:
            raise ProdutoIndisponivelError(f"Produto {produto_id} indisponível nesta filial.")
        if estoque.quantidade < quantidade:
            raise EstoqueInsuficienteError(
                f"Estoque insuficiente para {estoque.produto.nome}: "
                f"disponível {estoque.quantidade}, solicitado {quantidade}."
            )
        estoque.quantidade -= quantidade
    _salvar_saldos(list(estoques.values()))
    return estoques


@transaction.atomic
def devolver_itens(loja_id: int, quantidades: dict[int, int]) -> None:
    """Devolve ao estoque da filial as quantidades de um pedido cancelado."""
    estoques = _bloquear_estoques(loja_id, list(quantidades))
    for produto_id, quantidade in quantidades.items():
        estoque = estoques.get(produto_id)
        if estoque is not None:
            estoque.quantidade += quantidade
    _salvar_saldos(list(estoques.values()))

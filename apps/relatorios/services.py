"""Consultas agregadas dos relatórios.

As funções recebem um filtro de filial opcional (``None`` = todas) e um
período, e retornam estruturas simples (listas de dicionários) prontas para
serialização e cache.
"""

from datetime import date
from decimal import Decimal
from typing import Any

from django.db.models import Count, DecimalField, ExpressionWrapper, F, Q, QuerySet, Sum
from django.db.models.functions import Coalesce

from apps.estoque.models import EstoqueLocal
from apps.pedidos.models import ItemPedido, Pedido, StatusPedido

ZERO = Decimal("0.00")
VALOR_ITEM = ExpressionWrapper(
    F("quantidade") * F("preco_unitario"), output_field=DecimalField(max_digits=14, decimal_places=2)
)


def _periodo(queryset: QuerySet, campo: str, inicio: date | None, fim: date | None) -> QuerySet:
    """Filtra o queryset pelo intervalo de datas (inclusivo) do ``campo``."""
    if inicio:
        queryset = queryset.filter(**{f"{campo}__date__gte": inicio})
    if fim:
        queryset = queryset.filter(**{f"{campo}__date__lte": fim})
    return queryset


def vendas_por_loja(loja_id: int | None, inicio: date | None, fim: date | None) -> list[dict[str, Any]]:
    """Faturamento, quantidade de pedidos e ticket médio por filial.

    Considera apenas pedidos FINALIZADOS.
    """
    itens = _periodo(
        ItemPedido.objects.filter(pedido__status=StatusPedido.FINALIZADO), "pedido__data_criacao", inicio, fim
    )
    if loja_id is not None:
        itens = itens.filter(pedido__loja_id=loja_id)
    linhas = (
        itens.values("pedido__loja_id", "pedido__loja__nome")
        .annotate(faturamento=Coalesce(Sum(VALOR_ITEM), ZERO), pedidos=Count("pedido", distinct=True))
        .order_by("pedido__loja__nome")
    )
    return [
        {
            "loja_id": linha["pedido__loja_id"],
            "loja": linha["pedido__loja__nome"],
            "pedidos": linha["pedidos"],
            "faturamento": linha["faturamento"],
            "ticket_medio": (linha["faturamento"] / linha["pedidos"]).quantize(ZERO),
        }
        for linha in linhas
    ]


def produtos_mais_vendidos(
    loja_id: int | None, inicio: date | None, fim: date | None, limite: int = 10
) -> list[dict[str, Any]]:
    """Ranking de produtos por quantidade vendida em pedidos FINALIZADOS."""
    itens = _periodo(
        ItemPedido.objects.filter(pedido__status=StatusPedido.FINALIZADO), "pedido__data_criacao", inicio, fim
    )
    if loja_id is not None:
        itens = itens.filter(pedido__loja_id=loja_id)
    linhas = (
        itens.values("produto_id", "produto__nome", "produto__sku")
        .annotate(quantidade_vendida=Sum("quantidade"), faturamento=Coalesce(Sum(VALOR_ITEM), ZERO))
        .order_by("-quantidade_vendida", "produto__nome")[:limite]
    )
    return [
        {
            "produto_id": linha["produto_id"],
            "produto": linha["produto__nome"],
            "sku": linha["produto__sku"],
            "quantidade": linha["quantidade_vendida"],
            "faturamento": linha["faturamento"],
        }
        for linha in linhas
    ]


def pedidos_por_status(loja_id: int | None, inicio: date | None, fim: date | None) -> dict[str, int]:
    """Contagem de pedidos em cada status no período."""
    pedidos = _periodo(Pedido.objects.all(), "data_criacao", inicio, fim)
    if loja_id is not None:
        pedidos = pedidos.filter(loja_id=loja_id)
    contagem = pedidos.aggregate(**{status: Count("id", filter=Q(status=status)) for status in StatusPedido.values})
    return {status: contagem[status] for status in StatusPedido.values}


def estoque_abaixo_do_minimo(loja_id: int | None) -> list[dict[str, Any]]:
    """Produtos ativos com saldo igual ou abaixo do mínimo."""
    estoques = EstoqueLocal.objects.filter(quantidade__lte=F("quantidade_minima"), produto__ativo=True)
    if loja_id is not None:
        estoques = estoques.filter(loja_id=loja_id)
    return list(
        estoques.order_by("loja__nome", "produto__nome").values(
            "loja_id",
            "produto_id",
            "quantidade",
            "quantidade_minima",
            loja_nome=F("loja__nome"),
            produto_nome=F("produto__nome"),
        )
    )

"""Endpoints de relatórios gerenciais (ADMIN e GERENTE).

Os relatórios históricos ficam em cache (Redis) por ``CACHE_TTL_RELATORIOS``
segundos, com chave composta pelo relatório, filial e parâmetros da consulta.
O relatório de estoque baixo não usa cache: ele orienta a reposição e precisa
refletir o saldo atual.
"""

from typing import Any

from django.conf import settings
from django.core.cache import cache
from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import PermissionDenied
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.mixins import usuario_e_admin
from apps.core.permissions import IsGestao
from apps.relatorios import services
from apps.relatorios.serializers import (
    EstoqueBaixoSerializer,
    FiltroRelatorioSerializer,
    PedidosPorStatusSerializer,
    ProdutoVendidoSerializer,
    VendasLojaSerializer,
)

TAG = "Relatórios"


def resolver_loja(user: Any, loja_solicitada: int | None) -> int | None:
    """Define a filial do relatório conforme o perfil.

    ADMIN pode escolher qualquer filial (ou todas, com ``None``). GERENTE fica
    restrito à própria filial.
    """
    if usuario_e_admin(user):
        return loja_solicitada
    if loja_solicitada is not None and loja_solicitada != user.loja_id:
        raise PermissionDenied("Gerentes só consultam relatórios da própria filial.")
    return user.loja_id


class RelatorioBaseView(APIView):
    """Valida filtros, aplica o escopo de filial e cacheia o resultado."""

    permission_classes = (IsGestao,)
    nome_relatorio = ""
    usar_cache = True

    def calcular(self, loja_id: int | None, filtros: dict[str, Any]) -> Any:
        """Executa a consulta do relatório (implementado nas subclasses)."""
        raise NotImplementedError

    def get(self, request: Request) -> Response:
        """Retorna o relatório, usando o cache quando habilitado e disponível."""
        entrada = FiltroRelatorioSerializer(data=request.query_params)
        entrada.is_valid(raise_exception=True)
        filtros = entrada.validated_data
        loja_id = resolver_loja(request.user, filtros.get("loja"))
        if not self.usar_cache:
            return Response(self.calcular(loja_id, filtros))
        chave = ":".join(
            str(parte)
            for parte in (
                "relatorios",
                self.nome_relatorio,
                loja_id,
                filtros.get("inicio"),
                filtros.get("fim"),
                filtros["limite"],
            )
        )
        dados = cache.get(chave)
        if dados is None:
            dados = self.calcular(loja_id, filtros)
            cache.set(chave, dados, settings.CACHE_TTL_RELATORIOS)
        return Response(dados)


@extend_schema(
    tags=[TAG],
    summary="Vendas por filial",
    description="Faturamento, número de pedidos e ticket médio (apenas pedidos FINALIZADOS).",
    parameters=[FiltroRelatorioSerializer],
    responses=VendasLojaSerializer(many=True),
)
class VendasPorLojaView(RelatorioBaseView):
    """Relatório de vendas por filial."""

    nome_relatorio = "vendas"

    def calcular(self, loja_id: int | None, filtros: dict[str, Any]) -> Any:
        """Consulta o faturamento por filial."""
        return services.vendas_por_loja(loja_id, filtros.get("inicio"), filtros.get("fim"))


@extend_schema(
    tags=[TAG],
    summary="Produtos mais vendidos",
    description="Ranking por quantidade vendida em pedidos FINALIZADOS. Use ``limite`` (1 a 100).",
    parameters=[FiltroRelatorioSerializer],
    responses=ProdutoVendidoSerializer(many=True),
)
class ProdutosMaisVendidosView(RelatorioBaseView):
    """Ranking de produtos mais vendidos."""

    nome_relatorio = "mais-vendidos"

    def calcular(self, loja_id: int | None, filtros: dict[str, Any]) -> Any:
        """Consulta o ranking de produtos."""
        return services.produtos_mais_vendidos(loja_id, filtros.get("inicio"), filtros.get("fim"), filtros["limite"])


@extend_schema(
    tags=[TAG],
    summary="Pedidos por status",
    description="Quantidade de pedidos em cada status no período.",
    parameters=[FiltroRelatorioSerializer],
    responses=PedidosPorStatusSerializer,
)
class PedidosPorStatusView(RelatorioBaseView):
    """Contagem de pedidos por status."""

    nome_relatorio = "status"

    def calcular(self, loja_id: int | None, filtros: dict[str, Any]) -> Any:
        """Conta os pedidos de cada status."""
        return services.pedidos_por_status(loja_id, filtros.get("inicio"), filtros.get("fim"))


@extend_schema(
    tags=[TAG],
    summary="Estoque abaixo do mínimo",
    description=(
        "Produtos ativos que precisam de reposição, com o saldo atual (sem cache). "
        "Os parâmetros ``inicio``, ``fim`` e ``limite`` são ignorados."
    ),
    parameters=[FiltroRelatorioSerializer],
    responses=EstoqueBaixoSerializer(many=True),
)
class EstoqueBaixoView(RelatorioBaseView):
    """Itens com saldo abaixo do mínimo."""

    nome_relatorio = "estoque-baixo"
    usar_cache = False

    def calcular(self, loja_id: int | None, filtros: dict[str, Any]) -> Any:
        """Lista os itens a repor."""
        return services.estoque_abaixo_do_minimo(loja_id)

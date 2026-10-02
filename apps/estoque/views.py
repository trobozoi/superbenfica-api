"""Endpoints REST do app ``estoque``."""

import logging

from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from apps.core.mixins import LojaScopedQuerysetMixin, PermissoesPorAcaoMixin
from apps.core.permissions import IsEquipe, IsGestao
from apps.estoque.filters import EstoqueLocalFilter
from apps.estoque.models import EstoqueLocal
from apps.estoque.serializers import AjusteEstoqueSerializer, EstoqueLocalSerializer
from apps.estoque.services import ajustar_estoque

logger = logging.getLogger(__name__)

TAG = "Estoque"


@extend_schema_view(
    list=extend_schema(
        tags=[TAG],
        summary="Listar estoque",
        description=(
            "Funcionários veem o estoque da própria filial; ADMIN vê todas. "
            "Use ``abaixo_do_minimo=true`` para listar itens a repor."
        ),
    ),
    retrieve=extend_schema(tags=[TAG], summary="Detalhar estoque"),
    create=extend_schema(tags=[TAG], summary="Cadastrar produto no estoque da filial", description="ADMIN e GERENTE."),
    update=extend_schema(tags=[TAG], summary="Atualizar estoque", description="ADMIN e GERENTE."),
    partial_update=extend_schema(tags=[TAG], summary="Atualizar parcialmente estoque"),
    destroy=extend_schema(tags=[TAG], summary="Remover produto do estoque da filial"),
)
class EstoqueLocalViewSet(PermissoesPorAcaoMixin, LojaScopedQuerysetMixin, viewsets.ModelViewSet):
    """Estoque independente por filial."""

    queryset = EstoqueLocal.objects.select_related("produto", "loja")
    serializer_class = EstoqueLocalSerializer
    permission_classes = (IsGestao,)
    permissoes_por_acao = {"list": (IsEquipe,), "retrieve": (IsEquipe,)}
    filterset_class = EstoqueLocalFilter
    search_fields = ("produto__nome", "produto__sku")
    ordering_fields = ("quantidade", "produto__nome", "data_atualizacao")

    @extend_schema(
        tags=[TAG],
        summary="Ajustar saldo",
        description=(
            "Entrada (``delta`` positivo) ou saída (``delta`` negativo) manual. "
            "Retorna 409 se o saldo ficaria negativo. Publica ``estoque.atualizado`` no WebSocket."
        ),
        request=AjusteEstoqueSerializer,
        responses=EstoqueLocalSerializer,
    )
    @action(detail=True, methods=["post"])
    def ajustar(self, request: Request, pk: str | None = None) -> Response:
        """Aplica um ajuste manual de saldo com bloqueio de linha."""
        estoque = self.get_object()
        entrada = AjusteEstoqueSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        estoque = ajustar_estoque(estoque.pk, entrada.validated_data["delta"])
        # O motivo (texto livre) não vai para o log para evitar log injection (S5145).
        logger.info(
            "Ajuste de estoque %s: delta=%s usuario=%s",
            estoque.pk,
            entrada.validated_data["delta"],
            request.user.pk,
        )
        return Response(self.get_serializer(estoque).data)

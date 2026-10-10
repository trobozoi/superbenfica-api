"""Endpoints REST do app ``pedidos``.

Pedidos não são editados nem excluídos diretamente: cada mudança passa por
uma ação de fluxo (``cancelar``, ``iniciar-separacao``, ``despachar``,
``finalizar``) que valida o status, movimenta o estoque e publica eventos no
WebSocket.
"""

from django.db.models import QuerySet
from drf_spectacular.utils import OpenApiExample, extend_schema, extend_schema_view
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import BaseSerializer

from apps.core.constants import ROLES_GESTAO
from apps.core.mixins import PermissoesPorAcaoMixin, usuario_e_admin
from apps.core.permissions import IsEquipeSeparacao, IsEquipeVenda, usuario_tem_role
from apps.core.throttling import Escopo, ThrottlePorAcaoMixin
from apps.pedidos.models import Pedido, Separacao, StatusPedido
from apps.pedidos.serializers import (
    ItemPedidoSerializer,
    MarcarItemSerializer,
    PedidoCreateSerializer,
    PedidoSerializer,
    SeparacaoSerializer,
)
from apps.pedidos.services import (
    cancelar_pedido,
    concluir_separacao,
    despachar_pedido,
    finalizar_pedido,
    iniciar_separacao,
    marcar_item,
)

TAG_PEDIDOS = "Pedidos"
TAG_SEPARACOES = "Separações"
RESPOSTA_PEDIDO = {status.HTTP_200_OK: PedidoSerializer}


def filtrar_por_perfil(queryset: QuerySet, user: object, prefixo: str = "") -> QuerySet:
    """Restringe o queryset de pedidos (ou relacionados) ao perfil do usuário.

    - ADMIN: todos.
    - Funcionário: pedidos da própria filial.
    - CLIENTE: apenas os próprios pedidos.
    """
    if usuario_e_admin(user):
        return queryset
    if user.is_equipe:
        return queryset.filter(**{f"{prefixo}loja_id": user.loja_id})
    return queryset.filter(**{f"{prefixo}cliente__usuario": user})


@extend_schema_view(
    list=extend_schema(
        tags=[TAG_PEDIDOS],
        summary="Listar pedidos",
        description=(
            "ADMIN vê todos; funcionários veem os da própria filial; CLIENTE vê os próprios. "
            "Filtros: ``status``, ``loja``, ``cliente``, ``forma_pagamento``."
        ),
    ),
    retrieve=extend_schema(tags=[TAG_PEDIDOS], summary="Detalhar pedido"),
    create=extend_schema(
        tags=[TAG_PEDIDOS],
        summary="Criar pedido",
        description=(
            "Baixa o estoque da filial de forma atômica. Retorna **409** se faltar estoque. "
            "``forma_pagamento`` é obrigatória e deve estar ativa (veja ``GET /api/formas-pagamento/``). "
            "Publica ``pedido.criado`` no WebSocket. Limite: 30 pedidos/min por usuário (**429** ao exceder)."
        ),
        responses={status.HTTP_201_CREATED: PedidoSerializer},
        examples=[
            OpenApiExample(
                "Pedido de cliente",
                value={
                    "loja": 1,
                    "forma_pagamento": 1,
                    "itens": [{"produto": 1, "quantidade": 2}],
                    "observacao": "Sem sacolas",
                },
                request_only=True,
            ),
        ],
    ),
)
class PedidoViewSet(
    ThrottlePorAcaoMixin,
    PermissoesPorAcaoMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    """Pedidos e ações do fluxo de atendimento."""

    queryset = Pedido.objects.select_related("cliente", "loja", "forma_pagamento").prefetch_related(
        "itens__produto", "separacoes__usuario"
    )
    permission_classes = (IsAuthenticated,)
    permissoes_por_acao = {
        "iniciar_separacao": (IsEquipeSeparacao,),
        "despachar": (IsEquipeVenda,),
        "finalizar": (IsEquipeVenda,),
    }
    throttle_scopes_por_acao = {
        "create": Escopo.PEDIDOS_CRIACAO,
        "cancelar": Escopo.PEDIDOS_FLUXO,
        "iniciar_separacao": Escopo.PEDIDOS_FLUXO,
        "despachar": Escopo.PEDIDOS_FLUXO,
        "finalizar": Escopo.PEDIDOS_FLUXO,
    }
    filterset_fields = ("status", "loja", "cliente", "forma_pagamento", "tipo_entrega")
    search_fields = ("codigo", "cliente__nome")
    ordering_fields = ("data_criacao", "status")

    def get_queryset(self) -> QuerySet[Pedido]:
        """Aplica o escopo do perfil do usuário."""
        queryset = super().get_queryset()
        if getattr(self, "swagger_fake_view", False):
            return queryset.none()
        return filtrar_por_perfil(queryset, self.request.user)

    def get_serializer_class(self) -> type[BaseSerializer]:
        """Serializer de entrada na criação; de leitura nas demais ações."""
        return PedidoCreateSerializer if self.action == "create" else PedidoSerializer

    def _resposta(self, pedido_id: int) -> Response:
        """Recarrega o pedido com itens e separações e o serializa."""
        return Response(PedidoSerializer(self.get_queryset().get(pk=pedido_id)).data)

    @extend_schema(
        tags=[TAG_PEDIDOS],
        summary="Cancelar pedido",
        description="Devolve os itens ao estoque. O CLIENTE só cancela pedidos PENDENTES.",
        request=None,
        responses=RESPOSTA_PEDIDO,
    )
    @action(detail=True, methods=["post"])
    def cancelar(self, request: Request, pk: str | None = None) -> Response:
        """Cancela o pedido e devolve o estoque."""
        pedido = self.get_object()
        if not request.user.is_equipe and pedido.status != StatusPedido.PENDENTE:
            raise PermissionDenied("Clientes só podem cancelar pedidos pendentes.")
        cancelar_pedido(pedido.pk)
        return self._resposta(pedido.pk)

    @extend_schema(
        tags=[TAG_PEDIDOS],
        summary="Iniciar separação",
        description="ADMIN, GERENTE e SEPARADOR. Muda o pedido para EM_SEPARACAO.",
        request=None,
        responses={status.HTTP_201_CREATED: SeparacaoSerializer},
    )
    @action(detail=True, methods=["post"], url_path="iniciar-separacao")
    def iniciar_separacao(self, request: Request, pk: str | None = None) -> Response:
        """Registra o usuário atual como separador do pedido."""
        pedido = self.get_object()
        separacao = iniciar_separacao(pedido.pk, request.user)
        return Response(SeparacaoSerializer(separacao).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        tags=[TAG_PEDIDOS],
        summary="Saiu para entrega",
        description=(
            "ADMIN, GERENTE e CAIXA. Somente pedidos SEPARADOS com entrega em domicílio. "
            "Muda o pedido para SAIU_PARA_ENTREGA."
        ),
        request=None,
        responses=RESPOSTA_PEDIDO,
    )
    @action(detail=True, methods=["post"])
    def despachar(self, request: Request, pk: str | None = None) -> Response:
        """Registra que o pedido de entrega saiu da loja."""
        pedido = self.get_object()
        despachar_pedido(pedido.pk)
        return self._resposta(pedido.pk)

    @extend_schema(
        tags=[TAG_PEDIDOS],
        summary="Finalizar pedido",
        description=(
            "ADMIN, GERENTE e CAIXA. Retirada na loja: pedidos SEPARADOS. "
            "Entrega em domicílio: pedidos que SAIRAM PARA ENTREGA."
        ),
        request=None,
        responses=RESPOSTA_PEDIDO,
    )
    @action(detail=True, methods=["post"])
    def finalizar(self, request: Request, pk: str | None = None) -> Response:
        """Finaliza o pedido: retirado na loja ou entregue ao cliente."""
        pedido = self.get_object()
        finalizar_pedido(pedido.pk)
        return self._resposta(pedido.pk)


@extend_schema_view(
    list=extend_schema(
        tags=[TAG_SEPARACOES],
        summary="Listar separações",
        description="Separações da filial do usuário. Filtros: ``status``, ``usuario``, ``pedido``.",
    ),
    retrieve=extend_schema(tags=[TAG_SEPARACOES], summary="Detalhar separação"),
)
class SeparacaoViewSet(ThrottlePorAcaoMixin, viewsets.ReadOnlyModelViewSet):
    """Consulta de separações e conclusão pelo separador."""

    queryset = Separacao.objects.select_related("pedido", "usuario")
    serializer_class = SeparacaoSerializer
    permission_classes = (IsEquipeSeparacao,)
    throttle_scopes_por_acao = {"marcar_item": Escopo.PEDIDOS_FLUXO, "concluir": Escopo.PEDIDOS_FLUXO}
    filterset_fields = ("status", "usuario", "pedido")
    ordering_fields = ("data_inicio",)

    def get_queryset(self) -> QuerySet[Separacao]:
        """Restringe à filial do usuário."""
        queryset = super().get_queryset()
        if getattr(self, "swagger_fake_view", False):
            return queryset.none()
        return filtrar_por_perfil(queryset, self.request.user, prefixo="pedido__")

    def _exigir_responsavel(self, separacao: Separacao) -> None:
        """Só o separador responsável (ou ADMIN/GERENTE) mexe na separação."""
        user = self.request.user
        if not usuario_tem_role(user, ROLES_GESTAO) and separacao.usuario_id != user.pk:
            raise PermissionDenied("Somente o separador responsável pode alterar esta separação.")

    @extend_schema(
        tags=[TAG_SEPARACOES],
        summary="Marcar item separado",
        description=(
            "Checklist da separação: marca (ou desmarca) um item do pedido como já separado. "
            "Somente o separador responsável (ou ADMIN/GERENTE) e com a separação em andamento (**409** se não). "
            "Publica ``pedido.atualizado`` no WebSocket."
        ),
        request=MarcarItemSerializer,
        responses=ItemPedidoSerializer,
        examples=[OpenApiExample("Marcar", value={"item": 12, "separado": True}, request_only=True)],
    )
    @action(detail=True, methods=["post"], url_path="marcar-item")
    def marcar_item(self, request: Request, pk: str | None = None) -> Response:
        """Marca ou desmarca um item no checklist."""
        separacao = self.get_object()
        self._exigir_responsavel(separacao)
        entrada = MarcarItemSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        item = marcar_item(separacao.pk, entrada.validated_data["item"], entrada.validated_data["separado"])
        return Response(ItemPedidoSerializer(item).data)

    @extend_schema(
        tags=[TAG_SEPARACOES],
        summary="Concluir separação",
        description=("O próprio separador (ou ADMIN/GERENTE) conclui a separação. O pedido passa para SEPARADO."),
        request=None,
        responses=SeparacaoSerializer,
    )
    @action(detail=True, methods=["post"])
    def concluir(self, request: Request, pk: str | None = None) -> Response:
        """Conclui a separação em andamento."""
        separacao = self.get_object()
        self._exigir_responsavel(separacao)
        separacao = concluir_separacao(separacao.pk)
        return Response(SeparacaoSerializer(separacao).data)

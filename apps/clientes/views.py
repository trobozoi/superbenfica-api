"""Endpoints REST do app ``clientes``.

Funcionários consultam todos os clientes da rede (um cliente pode comprar em
qualquer filial). Um usuário com role CLIENTE vê e edita apenas o próprio
cadastro e os próprios endereços.
"""

from django.db.models import QuerySet
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from apps.clientes.models import Cliente, EnderecoCliente
from apps.clientes.serializers import ClienteSerializer, EnderecoClienteSerializer
from apps.core.mixins import PermissoesPorAcaoMixin
from apps.core.permissions import IsEquipeVenda, IsGestao

TAG_CLIENTES = "Clientes"


@extend_schema_view(
    list=extend_schema(
        tags=[TAG_CLIENTES],
        summary="Listar clientes",
        description="Funcionários veem todos; o CLIENTE vê apenas o próprio cadastro.",
    ),
    retrieve=extend_schema(tags=[TAG_CLIENTES], summary="Detalhar cliente"),
    create=extend_schema(
        tags=[TAG_CLIENTES],
        summary="Cadastrar cliente (balcão)",
        description="ADMIN, GERENTE e CAIXA. Para autocadastro use ``/api/auth/registrar/``.",
    ),
    update=extend_schema(tags=[TAG_CLIENTES], summary="Atualizar cliente"),
    partial_update=extend_schema(tags=[TAG_CLIENTES], summary="Atualizar parcialmente cliente"),
    destroy=extend_schema(tags=[TAG_CLIENTES], summary="Excluir cliente", description="ADMIN e GERENTE."),
)
class ClienteViewSet(PermissoesPorAcaoMixin, viewsets.ModelViewSet):
    """Cadastro de clientes."""

    queryset = Cliente.objects.select_related("loja").prefetch_related("enderecos")
    serializer_class = ClienteSerializer
    permission_classes = (IsAuthenticated,)
    permissoes_por_acao = {"create": (IsEquipeVenda,), "destroy": (IsGestao,)}
    filterset_fields = ("loja",)
    search_fields = ("nome", "email", "telefone")
    ordering_fields = ("nome", "data_cadastro")

    def get_queryset(self) -> QuerySet[Cliente]:
        """Clientes enxergam apenas o próprio cadastro."""
        queryset = super().get_queryset()
        if getattr(self, "swagger_fake_view", False) or self.request.user.is_equipe:
            return queryset
        return queryset.filter(usuario=self.request.user)


@extend_schema_view(
    list=extend_schema(tags=[TAG_CLIENTES], summary="Listar endereços", description="Filtro: ``cliente``."),
    retrieve=extend_schema(tags=[TAG_CLIENTES], summary="Detalhar endereço"),
    create=extend_schema(tags=[TAG_CLIENTES], summary="Cadastrar endereço"),
    update=extend_schema(tags=[TAG_CLIENTES], summary="Atualizar endereço"),
    partial_update=extend_schema(tags=[TAG_CLIENTES], summary="Atualizar parcialmente endereço"),
    destroy=extend_schema(tags=[TAG_CLIENTES], summary="Excluir endereço"),
)
class EnderecoClienteViewSet(viewsets.ModelViewSet):
    """Endereços de entrega dos clientes."""

    queryset = EnderecoCliente.objects.select_related("cliente")
    serializer_class = EnderecoClienteSerializer
    permission_classes = (IsAuthenticated,)
    filterset_fields = ("cliente", "cidade", "estado", "principal")

    def get_queryset(self) -> QuerySet[EnderecoCliente]:
        """Clientes enxergam apenas os próprios endereços."""
        queryset = super().get_queryset()
        if getattr(self, "swagger_fake_view", False) or self.request.user.is_equipe:
            return queryset
        return queryset.filter(cliente__usuario=self.request.user)

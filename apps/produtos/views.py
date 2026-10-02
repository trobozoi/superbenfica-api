"""Endpoints REST do app ``produtos``."""

from django.db.models import QuerySet
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from apps.core.mixins import PermissoesPorAcaoMixin
from apps.core.permissions import IsGestao
from apps.produtos.models import Produto
from apps.produtos.serializers import ProdutoSerializer

TAG = "Produtos"


@extend_schema_view(
    list=extend_schema(
        tags=[TAG],
        summary="Listar produtos",
        description="Clientes veem apenas produtos ativos. Filtros: ``categoria``, ``ativo``; busca por nome/SKU.",
    ),
    retrieve=extend_schema(tags=[TAG], summary="Detalhar produto"),
    create=extend_schema(tags=[TAG], summary="Cadastrar produto", description="ADMIN e GERENTE."),
    update=extend_schema(tags=[TAG], summary="Atualizar produto", description="ADMIN e GERENTE."),
    partial_update=extend_schema(tags=[TAG], summary="Atualizar parcialmente produto"),
    destroy=extend_schema(
        tags=[TAG],
        summary="Desativar produto",
        description="O produto é desativado (``ativo=false``) para preservar o histórico de pedidos.",
    ),
)
class ProdutoViewSet(PermissoesPorAcaoMixin, viewsets.ModelViewSet):
    """Catálogo de produtos. Leitura para todos; escrita para a gestão."""

    queryset = Produto.objects.all()
    serializer_class = ProdutoSerializer
    permission_classes = (IsGestao,)
    permissoes_por_acao = {"list": (IsAuthenticated,), "retrieve": (IsAuthenticated,)}
    filterset_fields = ("categoria", "ativo")
    search_fields = ("nome", "sku", "descricao")
    ordering_fields = ("nome", "preco", "data_criacao")

    def get_queryset(self) -> QuerySet[Produto]:
        """Oculta produtos inativos de quem não é funcionário."""
        queryset = super().get_queryset()
        if getattr(self, "swagger_fake_view", False):
            return queryset
        if not self.request.user.is_equipe:
            return queryset.filter(ativo=True)
        return queryset

    def perform_destroy(self, instance: Produto) -> None:
        """Desativa o produto em vez de excluí-lo."""
        instance.ativo = False
        instance.save(update_fields=["ativo", "data_atualizacao"])

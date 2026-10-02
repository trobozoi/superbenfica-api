"""Endpoints REST do app ``filiais``."""

from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from apps.core.mixins import PermissoesPorAcaoMixin
from apps.core.permissions import IsAdmin
from apps.filiais.models import Loja
from apps.filiais.serializers import LojaSerializer

TAG = "Filiais"


@extend_schema_view(
    list=extend_schema(tags=[TAG], summary="Listar filiais", description="Qualquer usuário autenticado."),
    retrieve=extend_schema(tags=[TAG], summary="Detalhar filial"),
    create=extend_schema(tags=[TAG], summary="Cadastrar filial", description="Somente ADMIN."),
    update=extend_schema(tags=[TAG], summary="Atualizar filial", description="Somente ADMIN."),
    partial_update=extend_schema(tags=[TAG], summary="Atualizar parcialmente filial"),
    destroy=extend_schema(
        tags=[TAG],
        summary="Desativar filial",
        description="Somente ADMIN. A filial é desativada (``ativa=false``), não removida.",
    ),
)
class LojaViewSet(PermissoesPorAcaoMixin, viewsets.ModelViewSet):
    """CRUD de filiais. Escrita restrita a administradores."""

    queryset = Loja.objects.all()
    serializer_class = LojaSerializer
    permission_classes = (IsAdmin,)
    permissoes_por_acao = {"list": (IsAuthenticated,), "retrieve": (IsAuthenticated,)}
    filterset_fields = ("ativa",)
    search_fields = ("nome", "endereco")
    ordering_fields = ("nome", "data_criacao")

    def perform_destroy(self, instance: Loja) -> None:
        """Desativa a filial em vez de excluí-la (preserva o histórico)."""
        instance.ativa = False
        instance.save(update_fields=["ativa", "data_atualizacao"])

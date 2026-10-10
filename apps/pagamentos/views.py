"""Endpoints REST do app ``pagamentos``."""

from django.db.models import QuerySet
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from apps.core.mixins import PermissoesPorAcaoMixin
from apps.core.permissions import IsAdmin
from apps.pagamentos.models import FormaPagamento
from apps.pagamentos.serializers import FormaPagamentoSerializer

TAG = "Formas de pagamento"


@extend_schema_view(
    list=extend_schema(
        tags=[TAG],
        summary="Listar formas de pagamento",
        description=(
            "Qualquer usuário autenticado. Clientes veem apenas as formas ativas. Filtros: ``tipo``, ``ativa``."
        ),
    ),
    retrieve=extend_schema(tags=[TAG], summary="Detalhar forma de pagamento"),
    create=extend_schema(tags=[TAG], summary="Cadastrar forma de pagamento", description="Somente ADMIN."),
    update=extend_schema(tags=[TAG], summary="Atualizar forma de pagamento", description="Somente ADMIN."),
    partial_update=extend_schema(tags=[TAG], summary="Atualizar parcialmente forma de pagamento"),
    destroy=extend_schema(
        tags=[TAG],
        summary="Desativar forma de pagamento",
        description="Somente ADMIN. A forma é desativada (``ativa=false``) para preservar o histórico dos pedidos.",
    ),
)
class FormaPagamentoViewSet(PermissoesPorAcaoMixin, viewsets.ModelViewSet):
    """Cadastro das formas de pagamento. Escrita restrita a administradores."""

    queryset = FormaPagamento.objects.all()
    serializer_class = FormaPagamentoSerializer
    permission_classes = (IsAdmin,)
    permissoes_por_acao = {"list": (IsAuthenticated,), "retrieve": (IsAuthenticated,)}
    filterset_fields = ("tipo", "ativa")
    search_fields = ("nome",)
    ordering_fields = ("ordem", "nome")

    def get_queryset(self) -> QuerySet[FormaPagamento]:
        """Oculta formas inativas de quem não é funcionário."""
        queryset = super().get_queryset()
        if getattr(self, "swagger_fake_view", False) or self.request.user.is_equipe:
            return queryset
        return queryset.filter(ativa=True)

    def perform_destroy(self, instance: FormaPagamento) -> None:
        """Desativa a forma de pagamento em vez de excluí-la."""
        instance.ativa = False
        instance.save(update_fields=["ativa", "data_atualizacao"])

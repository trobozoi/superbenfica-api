"""Rotas REST do app ``pagamentos`` (``/api/formas-pagamento/``)."""

from rest_framework.routers import DefaultRouter

from apps.pagamentos.views import FormaPagamentoViewSet

router = DefaultRouter()
router.register("formas-pagamento", FormaPagamentoViewSet, basename="forma-pagamento")

urlpatterns = router.urls

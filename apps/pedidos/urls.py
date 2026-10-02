"""Rotas REST do app ``pedidos`` (``/api/pedidos/`` e ``/api/separacoes/``)."""

from rest_framework.routers import DefaultRouter

from apps.pedidos.views import PedidoViewSet, SeparacaoViewSet

router = DefaultRouter()
router.register("pedidos", PedidoViewSet, basename="pedido")
router.register("separacoes", SeparacaoViewSet, basename="separacao")

urlpatterns = router.urls

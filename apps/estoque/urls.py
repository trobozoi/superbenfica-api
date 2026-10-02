"""Rotas REST do app ``estoque`` (``/api/estoques/``)."""

from rest_framework.routers import DefaultRouter

from apps.estoque.views import EstoqueLocalViewSet

router = DefaultRouter()
router.register("estoques", EstoqueLocalViewSet, basename="estoque")

urlpatterns = router.urls

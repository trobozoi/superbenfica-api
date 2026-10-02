"""Rotas REST do app ``produtos`` (``/api/produtos/``)."""

from rest_framework.routers import DefaultRouter

from apps.produtos.views import ProdutoViewSet

router = DefaultRouter()
router.register("produtos", ProdutoViewSet, basename="produto")

urlpatterns = router.urls

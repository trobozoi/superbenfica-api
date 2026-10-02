"""Rotas REST do app ``filiais`` (``/api/lojas/``)."""

from rest_framework.routers import DefaultRouter

from apps.filiais.views import LojaViewSet

router = DefaultRouter()
router.register("lojas", LojaViewSet, basename="loja")

urlpatterns = router.urls

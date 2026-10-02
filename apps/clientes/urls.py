"""Rotas REST do app ``clientes`` (``/api/clientes/`` e ``/api/enderecos/``)."""

from rest_framework.routers import DefaultRouter

from apps.clientes.views import ClienteViewSet, EnderecoClienteViewSet

router = DefaultRouter()
router.register("clientes", ClienteViewSet, basename="cliente")
router.register("enderecos", EnderecoClienteViewSet, basename="endereco")

urlpatterns = router.urls

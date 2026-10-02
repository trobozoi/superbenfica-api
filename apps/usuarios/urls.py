"""Rotas REST de usuários (``/api/usuarios/``)."""

from rest_framework.routers import DefaultRouter

from apps.usuarios.views import UsuarioViewSet

router = DefaultRouter()
router.register("usuarios", UsuarioViewSet, basename="usuario")

urlpatterns = router.urls

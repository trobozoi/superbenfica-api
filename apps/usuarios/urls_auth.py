"""Rotas de autenticação (``/api/auth/``)."""

from django.urls import path

from apps.usuarios.views import (
    LoginView,
    LogoutView,
    RegistroClienteView,
    RenovarTokenView,
    VerificarTokenView,
)

urlpatterns = [
    path("token/", LoginView.as_view(), name="token-obter"),
    path("token/refresh/", RenovarTokenView.as_view(), name="token-renovar"),
    path("token/verify/", VerificarTokenView.as_view(), name="token-verificar"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("registrar/", RegistroClienteView.as_view(), name="registrar-cliente"),
]

"""Configuração do app ``usuarios``."""

from django.apps import AppConfig


class UsuariosConfig(AppConfig):
    """Registro do app de usuários."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.usuarios"
    verbose_name = "Usuários"

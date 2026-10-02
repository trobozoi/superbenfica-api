"""Configuração do app ``clientes``."""

from django.apps import AppConfig


class ClientesConfig(AppConfig):
    """Registro do app de clientes."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.clientes"
    verbose_name = "Clientes"

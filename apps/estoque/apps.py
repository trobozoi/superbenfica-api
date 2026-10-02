"""Configuração do app ``estoque``."""

from django.apps import AppConfig


class EstoqueConfig(AppConfig):
    """Registro do app de estoque por filial."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.estoque"
    verbose_name = "Estoque"

"""Configuração do app ``produtos``."""

from django.apps import AppConfig


class ProdutosConfig(AppConfig):
    """Registro do app de catálogo de produtos."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.produtos"
    verbose_name = "Produtos"

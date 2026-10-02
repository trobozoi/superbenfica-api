"""Configuração do app ``pedidos``."""

from django.apps import AppConfig


class PedidosConfig(AppConfig):
    """Registro do app de pedidos."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.pedidos"
    verbose_name = "Pedidos"

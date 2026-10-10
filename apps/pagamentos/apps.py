"""Configuração do app ``pagamentos``."""

from django.apps import AppConfig


class PagamentosConfig(AppConfig):
    """Registro do app de formas de pagamento."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.pagamentos"
    verbose_name = "Pagamentos"

"""Configuração do app ``core``."""

from django.apps import AppConfig


class CoreConfig(AppConfig):
    """Registro do app de infraestrutura compartilhada."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"
    verbose_name = "Núcleo"

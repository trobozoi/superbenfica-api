"""Configuração do app ``filiais``."""

from django.apps import AppConfig


class FiliaisConfig(AppConfig):
    """Registro do app de lojas/filiais."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.filiais"
    verbose_name = "Filiais"

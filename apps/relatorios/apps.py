"""Configuração do app ``relatorios``."""

from django.apps import AppConfig


class RelatoriosConfig(AppConfig):
    """Registro do app de relatórios (sem models próprios)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.relatorios"
    verbose_name = "Relatórios"

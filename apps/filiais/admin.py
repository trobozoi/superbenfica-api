"""Configuração do Django Admin para filiais."""

from django.contrib import admin

from apps.filiais.models import Loja


@admin.register(Loja)
class LojaAdmin(admin.ModelAdmin):
    """Listagem e busca de lojas no admin."""

    list_display = ("nome", "telefone", "horario_abertura", "horario_fechamento", "ativa")
    list_filter = ("ativa",)
    search_fields = ("nome", "endereco")

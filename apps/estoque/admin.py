"""Configuração do Django Admin para o estoque."""

from django.contrib import admin

from apps.estoque.models import EstoqueLocal


@admin.register(EstoqueLocal)
class EstoqueLocalAdmin(admin.ModelAdmin):
    """Listagem do estoque por filial com filtros."""

    list_display = ("produto", "loja", "quantidade", "quantidade_minima", "data_atualizacao")
    list_filter = ("loja",)
    search_fields = ("produto__nome", "produto__sku")
    list_select_related = ("produto", "loja")

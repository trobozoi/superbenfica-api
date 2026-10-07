"""Configuração do Django Admin para produtos."""

from django.contrib import admin

from apps.produtos.models import Produto


@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    """Listagem, filtros e busca de produtos no admin."""

    list_display = ("nome", "sku", "codigo_barras", "categoria", "preco", "ativo")
    list_filter = ("categoria", "ativo")
    search_fields = ("nome", "sku", "codigo_barras")

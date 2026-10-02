"""Configuração do Django Admin para pedidos.

O admin é somente leitura para status e itens: alterações de fluxo devem
passar pela API, que movimenta o estoque e publica os eventos.
"""

from django.contrib import admin

from apps.pedidos.models import ItemPedido, Pedido, Separacao


class ItemPedidoInline(admin.TabularInline):
    """Itens exibidos dentro do pedido."""

    model = ItemPedido
    extra = 0
    readonly_fields = ("produto", "quantidade", "preco_unitario")
    can_delete = False


class SeparacaoInline(admin.TabularInline):
    """Separações exibidas dentro do pedido."""

    model = Separacao
    extra = 0
    readonly_fields = ("usuario", "status", "data_inicio", "data_conclusao")
    can_delete = False


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    """Consulta de pedidos no admin."""

    list_display = ("codigo", "cliente", "loja", "status", "data_criacao")
    list_filter = ("status", "loja")
    search_fields = ("codigo", "cliente__nome")
    readonly_fields = ("codigo", "status", "data_criacao", "data_atualizacao")
    list_select_related = ("cliente", "loja")
    inlines = (ItemPedidoInline, SeparacaoInline)

"""Configuração do Django Admin para formas de pagamento."""

from django.contrib import admin

from apps.pagamentos.models import FormaPagamento


@admin.register(FormaPagamento)
class FormaPagamentoAdmin(admin.ModelAdmin):
    """Listagem e edição rápida das formas de pagamento."""

    list_display = ("nome", "tipo", "permite_troco", "ativa", "ordem")
    list_editable = ("ativa", "ordem")
    list_filter = ("tipo", "ativa")
    search_fields = ("nome",)

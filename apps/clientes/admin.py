"""Configuração do Django Admin para clientes e endereços."""

from django.contrib import admin

from apps.clientes.models import Cliente, EnderecoCliente


class EnderecoClienteInline(admin.TabularInline):
    """Edição dos endereços dentro da tela do cliente."""

    model = EnderecoCliente
    extra = 0


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    """Listagem e busca de clientes no admin."""

    list_display = ("nome", "email", "telefone", "loja", "data_cadastro")
    list_filter = ("loja",)
    search_fields = ("nome", "email", "telefone")
    inlines = (EnderecoClienteInline,)

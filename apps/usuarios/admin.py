"""Configuração do Django Admin para o usuário customizado."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from apps.usuarios.models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    """Admin adaptado ao login por e-mail e aos campos de perfil."""

    ordering = ("nome",)
    list_display = ("nome", "email", "role", "loja", "is_active")
    list_filter = ("role", "loja", "is_active", "is_staff")
    search_fields = ("nome", "email")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Dados pessoais", {"fields": ("nome", "telefone")}),
        ("Perfil", {"fields": ("role", "loja")}),
        ("Permissões", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Datas", {"fields": ("last_login", "data_cadastro")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("email", "nome", "role", "loja", "password1", "password2")}),
    )

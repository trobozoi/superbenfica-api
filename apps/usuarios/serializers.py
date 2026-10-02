"""Serializers do app ``usuarios`` (cadastro, perfil e JWT)."""

from typing import Any

from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.clientes.models import Cliente
from apps.core.constants import Role
from apps.core.mixins import usuario_e_admin
from apps.filiais.models import Loja
from apps.usuarios.models import Usuario

CAMPOS_USUARIO = ("id", "nome", "email", "telefone", "loja", "role", "is_active", "data_cadastro")


class UsuarioSerializer(serializers.ModelSerializer):
    """Leitura e atualização de usuários (sem senha)."""

    loja_nome = serializers.CharField(source="loja.nome", read_only=True, default=None)

    class Meta:
        model = Usuario
        fields = (*CAMPOS_USUARIO, "loja_nome")
        read_only_fields = ("data_cadastro",)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Gerentes não criam admins nem operam usuários de outra filial."""
        request = self.context.get("request")
        if request is None or usuario_e_admin(request.user):
            return attrs
        if attrs.get("role") == Role.ADMIN:
            raise serializers.ValidationError({"role": "Somente administradores criam administradores."})
        loja = attrs.get("loja", getattr(self.instance, "loja", None))
        if loja is None or loja.pk != request.user.loja_id:
            raise serializers.ValidationError({"loja": "Informe a sua própria filial."})
        return attrs


class UsuarioCreateSerializer(UsuarioSerializer):
    """Criação de usuário com senha validada pelas regras do Django."""

    password = serializers.CharField(write_only=True, style={"input_type": "password"})

    class Meta(UsuarioSerializer.Meta):
        fields = (*UsuarioSerializer.Meta.fields, "password")

    def validate_password(self, value: str) -> str:
        """Aplica os validadores de senha configurados em ``AUTH_PASSWORD_VALIDATORS``."""
        validate_password(value)
        return value

    def create(self, validated_data: dict[str, Any]) -> Usuario:
        """Cria o usuário com a senha criptografada."""
        password = validated_data.pop("password")
        return Usuario.objects.create_user(password=password, **validated_data)


class RegistroClienteSerializer(serializers.Serializer):
    """Autocadastro público de clientes (cria ``Usuario`` + ``Cliente``)."""

    nome = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    telefone = serializers.CharField(max_length=20, required=False, allow_blank=True, default="")
    password = serializers.CharField(write_only=True, style={"input_type": "password"})
    loja = serializers.PrimaryKeyRelatedField(
        queryset=Loja.objects.filter(ativa=True), required=False, allow_null=True, default=None
    )

    def validate_email(self, value: str) -> str:
        """Garante e-mail único entre usuários e clientes."""
        email = value.lower()
        if Usuario.objects.filter(email=email).exists() or Cliente.objects.filter(email=email).exists():
            raise serializers.ValidationError("Este e-mail já está cadastrado.")
        return email

    def validate_password(self, value: str) -> str:
        """Aplica os validadores de senha do Django."""
        validate_password(value)
        return value

    @transaction.atomic
    def create(self, validated_data: dict[str, Any]) -> Usuario:
        """Cria o usuário com role CLIENTE e o cadastro de cliente vinculado."""
        usuario = Usuario.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            nome=validated_data["nome"],
            telefone=validated_data["telefone"],
            loja=validated_data["loja"],
            role=Role.CLIENTE,
        )
        Cliente.objects.create(
            usuario=usuario,
            nome=usuario.nome,
            email=usuario.email,
            telefone=usuario.telefone,
            loja=usuario.loja,
        )
        return usuario

    def to_representation(self, instance: Usuario) -> dict[str, Any]:
        """Retorna o usuário criado no mesmo formato de ``UsuarioSerializer``."""
        return UsuarioSerializer(instance, context=self.context).data


class TokenComPerfilSerializer(TokenObtainPairSerializer):
    """Emite o par de tokens JWT incluindo ``nome``, ``role`` e ``loja_id``."""

    @classmethod
    def get_token(cls, user: Usuario) -> Any:
        """Adiciona as claims de perfil ao token."""
        token = super().get_token(user)
        token["nome"] = user.nome
        token["role"] = user.role
        token["loja_id"] = user.loja_id
        return token

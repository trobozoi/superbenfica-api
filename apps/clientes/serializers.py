"""Serializers do app ``clientes``."""

from typing import Any

from rest_framework import serializers

from apps.clientes.models import Cliente, EnderecoCliente


class EnderecoClienteSerializer(serializers.ModelSerializer):
    """Endereço de entrega de um cliente."""

    class Meta:
        model = EnderecoCliente
        fields = (
            "id",
            "cliente",
            "endereco",
            "numero",
            "complemento",
            "bairro",
            "cidade",
            "estado",
            "cep",
            "principal",
        )

    def validate_cliente(self, value: Cliente) -> Cliente:
        """Clientes só cadastram endereços para si mesmos."""
        user = self.context["request"].user
        if not user.is_equipe and value.usuario_id != user.pk:
            raise serializers.ValidationError("Você só pode cadastrar os seus próprios endereços.")
        return value

    def validate_cep(self, value: str) -> str:
        """Normaliza o CEP para o formato ``00000-000``."""
        digitos = value.replace("-", "")
        return f"{digitos[:5]}-{digitos[5:]}"


class ClienteSerializer(serializers.ModelSerializer):
    """Cliente com a lista (somente leitura) dos seus endereços."""

    enderecos = EnderecoClienteSerializer(many=True, read_only=True)

    class Meta:
        model = Cliente
        fields = ("id", "usuario", "nome", "email", "telefone", "loja", "data_cadastro", "enderecos")
        read_only_fields = ("usuario", "data_cadastro")

    def validate_email(self, value: str) -> str:
        """Armazena o e-mail em minúsculas."""
        return value.lower()

    def update(self, instance: Cliente, validated_data: dict[str, Any]) -> Cliente:
        """Mantém nome/telefone do usuário vinculado sincronizados."""
        cliente = super().update(instance, validated_data)
        if cliente.usuario_id:
            cliente.usuario.nome = cliente.nome
            cliente.usuario.telefone = cliente.telefone
            cliente.usuario.save(update_fields=["nome", "telefone"])
        return cliente

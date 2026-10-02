"""Serializers do app ``estoque``."""

from typing import Any

from rest_framework import serializers

from apps.core.mixins import validar_loja_do_usuario
from apps.estoque.models import EstoqueLocal


class EstoqueLocalSerializer(serializers.ModelSerializer):
    """Saldo de um produto em uma filial."""

    produto_nome = serializers.CharField(source="produto.nome", read_only=True)
    produto_sku = serializers.CharField(source="produto.sku", read_only=True)
    loja_nome = serializers.CharField(source="loja.nome", read_only=True)
    abaixo_do_minimo = serializers.BooleanField(read_only=True)

    class Meta:
        model = EstoqueLocal
        fields = (
            "id",
            "produto",
            "produto_nome",
            "produto_sku",
            "loja",
            "loja_nome",
            "quantidade",
            "quantidade_minima",
            "abaixo_do_minimo",
            "data_atualizacao",
        )
        read_only_fields = ("data_atualizacao",)

    def validate_quantidade(self, value: int) -> int:
        """Não permite saldo negativo."""
        if value < 0:
            raise serializers.ValidationError("A quantidade não pode ser negativa.")
        return value

    def validate_quantidade_minima(self, value: int) -> int:
        """Não permite mínimo negativo."""
        if value < 0:
            raise serializers.ValidationError("A quantidade mínima não pode ser negativa.")
        return value

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Gerentes só alteram o estoque da própria filial."""
        loja = attrs.get("loja", getattr(self.instance, "loja", None))
        validar_loja_do_usuario(self.context["request"].user, getattr(loja, "pk", None))
        return attrs


class AjusteEstoqueSerializer(serializers.Serializer):
    """Entrada (positivo) ou saída (negativo) manual de mercadoria."""

    delta = serializers.IntegerField(help_text="Quantidade a somar (ou subtrair, se negativa).")
    motivo = serializers.CharField(max_length=255, help_text="Ex.: recebimento de fornecedor, perda, inventário.")

    def validate_delta(self, value: int) -> int:
        """O ajuste precisa alterar o saldo."""
        if value == 0:
            raise serializers.ValidationError("O ajuste deve ser diferente de zero.")
        return value

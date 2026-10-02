"""Serializers do app ``relatorios``.

Validam os parâmetros de consulta e descrevem o formato das respostas para a
documentação OpenAPI.
"""

from typing import Any

from rest_framework import serializers


class FiltroRelatorioSerializer(serializers.Serializer):
    """Parâmetros de consulta comuns aos relatórios."""

    loja = serializers.IntegerField(
        required=False, min_value=1, help_text="Somente ADMIN; gerentes usam a própria filial."
    )
    inicio = serializers.DateField(required=False, help_text="Data inicial (AAAA-MM-DD), inclusiva.")
    fim = serializers.DateField(required=False, help_text="Data final (AAAA-MM-DD), inclusiva.")
    limite = serializers.IntegerField(required=False, min_value=1, max_value=100, default=10)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Garante que o início não seja posterior ao fim."""
        inicio, fim = attrs.get("inicio"), attrs.get("fim")
        if inicio and fim and inicio > fim:
            raise serializers.ValidationError({"fim": "A data final deve ser igual ou posterior à inicial."})
        return attrs


class VendasLojaSerializer(serializers.Serializer):
    """Linha do relatório de vendas por filial."""

    loja_id = serializers.IntegerField()
    loja = serializers.CharField()
    pedidos = serializers.IntegerField()
    faturamento = serializers.DecimalField(max_digits=14, decimal_places=2)
    ticket_medio = serializers.DecimalField(max_digits=14, decimal_places=2)


class ProdutoVendidoSerializer(serializers.Serializer):
    """Linha do ranking de produtos mais vendidos."""

    produto_id = serializers.IntegerField()
    produto = serializers.CharField()
    sku = serializers.CharField()
    quantidade = serializers.IntegerField()
    faturamento = serializers.DecimalField(max_digits=14, decimal_places=2)


class PedidosPorStatusSerializer(serializers.Serializer):
    """Quantidade de pedidos em cada status."""

    PENDENTE = serializers.IntegerField()
    EM_SEPARACAO = serializers.IntegerField()
    SEPARADO = serializers.IntegerField()
    FINALIZADO = serializers.IntegerField()
    CANCELADO = serializers.IntegerField()


class EstoqueBaixoSerializer(serializers.Serializer):
    """Item com saldo abaixo do mínimo."""

    loja_id = serializers.IntegerField()
    loja_nome = serializers.CharField()
    produto_id = serializers.IntegerField()
    produto_nome = serializers.CharField()
    quantidade = serializers.IntegerField()
    quantidade_minima = serializers.IntegerField()

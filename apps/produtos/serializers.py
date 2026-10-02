"""Serializers do app ``produtos``."""

from rest_framework import serializers

from apps.produtos.models import Produto


class ProdutoSerializer(serializers.ModelSerializer):
    """Representação completa de um produto do catálogo."""

    class Meta:
        model = Produto
        fields = (
            "id",
            "nome",
            "descricao",
            "categoria",
            "preco",
            "sku",
            "ativo",
            "data_criacao",
            "data_atualizacao",
        )
        read_only_fields = ("data_criacao", "data_atualizacao")

    def validate_sku(self, value: str) -> str:
        """Normaliza o SKU para maiúsculas, sem espaços nas pontas."""
        return value.strip().upper()

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
            "codigo_barras",
            "ativo",
            "foto",
            "data_criacao",
            "data_atualizacao",
        )
        # A foto é enviada por POST /produtos/{id}/foto/ (multipart), nunca no JSON.
        read_only_fields = ("foto", "data_criacao", "data_atualizacao")

    def validate_sku(self, value: str) -> str:
        """Normaliza o SKU para maiúsculas, sem espaços nas pontas."""
        return value.strip().upper()

    def validate_codigo_barras(self, value: str) -> str:
        """Garante que o código (quando informado) não pertence a outro produto."""
        outros = Produto.objects.filter(codigo_barras=value)
        if self.instance is not None:
            outros = outros.exclude(pk=self.instance.pk)
        if value and outros.exists():
            raise serializers.ValidationError("Já existe um produto com este código de barras.")
        return value


class FotoProdutoSerializer(serializers.Serializer):
    """Upload da foto (multipart/form-data, campo ``foto``)."""

    foto = serializers.FileField(
        help_text="Imagem JPEG, PNG ou WebP de até 2 MB. É convertida para WebP (máx. 1200 px).",
    )

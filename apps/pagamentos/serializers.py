"""Serializers do app ``pagamentos``."""

from rest_framework import serializers

from apps.pagamentos.models import FormaPagamento


class FormaPagamentoSerializer(serializers.ModelSerializer):
    """Forma de pagamento aceita pela rede."""

    tipo_display = serializers.CharField(source="get_tipo_display", read_only=True)

    class Meta:
        model = FormaPagamento
        fields = (
            "id",
            "nome",
            "tipo",
            "tipo_display",
            "permite_troco",
            "ativa",
            "ordem",
            "data_criacao",
            "data_atualizacao",
        )
        read_only_fields = ("data_criacao", "data_atualizacao")

    def validate_nome(self, value: str) -> str:
        """Remove espaços nas pontas do nome."""
        return value.strip()

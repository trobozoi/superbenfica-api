"""Serializers do app ``filiais``."""

from typing import Any

from rest_framework import serializers

from apps.filiais.models import Loja


class LojaSerializer(serializers.ModelSerializer):
    """Representação completa de uma loja/filial."""

    class Meta:
        model = Loja
        fields = (
            "id",
            "nome",
            "endereco",
            "telefone",
            "horario_abertura",
            "horario_fechamento",
            "ativa",
            "data_criacao",
            "data_atualizacao",
        )
        read_only_fields = ("data_criacao", "data_atualizacao")

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Impede horários de abertura e fechamento iguais."""
        abertura = attrs.get("horario_abertura", getattr(self.instance, "horario_abertura", None))
        fechamento = attrs.get("horario_fechamento", getattr(self.instance, "horario_fechamento", None))
        if abertura is not None and abertura == fechamento:
            raise serializers.ValidationError({"horario_fechamento": "O fechamento deve ser diferente da abertura."})
        return attrs

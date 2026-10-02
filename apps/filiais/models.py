"""Models do app ``filiais``."""

from datetime import time

from django.db import models

from apps.core.models import TimeStampedModel


class Loja(TimeStampedModel):
    """Loja/filial da rede. Cada filial possui estoque independente."""

    nome = models.CharField("nome", max_length=120, unique=True)
    endereco = models.CharField("endereço", max_length=255)
    telefone = models.CharField("telefone", max_length=20, blank=True, default="")
    horario_abertura = models.TimeField("horário de abertura")
    horario_fechamento = models.TimeField("horário de fechamento")
    ativa = models.BooleanField("ativa", default=True)

    class Meta:
        db_table = "sb_loja"
        ordering = ["nome"]
        verbose_name = "loja"
        verbose_name_plural = "lojas"

    def __str__(self) -> str:
        return self.nome

    def esta_aberta(self, horario: time) -> bool:
        """Indica se a loja está aberta no ``horario`` informado.

        Suporta lojas que fecham após a meia-noite (fechamento < abertura).
        """
        if self.horario_abertura <= self.horario_fechamento:
            return self.horario_abertura <= horario < self.horario_fechamento
        return horario >= self.horario_abertura or horario < self.horario_fechamento

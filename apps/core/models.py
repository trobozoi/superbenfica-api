"""Models abstratos reutilizados pelos demais apps."""

from django.db import models


class TimeStampedModel(models.Model):
    """Adiciona as datas de criação e de última atualização ao model."""

    data_criacao = models.DateTimeField("data de criação", auto_now_add=True)
    data_atualizacao = models.DateTimeField("data de atualização", auto_now=True)

    class Meta:
        abstract = True

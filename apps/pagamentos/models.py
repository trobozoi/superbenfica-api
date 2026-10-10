"""Models do app ``pagamentos``.

As formas de pagamento ficam em tabela (e não fixas no código) para que a
rede possa ativar, desativar ou cadastrar variações, como um vale-alimentação
de bandeira específica, sem alterar o sistema.
"""

from django.db import models

from apps.core.models import TimeStampedModel


class TipoPagamento(models.TextChoices):
    """Meio de pagamento, usado para regras e relatórios."""

    PIX = "PIX", "Pix"
    CREDITO = "CREDITO", "Cartão de crédito"
    DEBITO = "DEBITO", "Cartão de débito"
    DINHEIRO = "DINHEIRO", "Dinheiro"
    VALE_ALIMENTACAO = "VALE_ALIMENTACAO", "Vale-alimentação"


class FormaPagamento(TimeStampedModel):
    """Forma de pagamento aceita pela rede."""

    nome = models.CharField("nome", max_length=60, unique=True)
    tipo = models.CharField("tipo", max_length=20, choices=TipoPagamento.choices)
    permite_troco = models.BooleanField(
        "permite troco", default=False, help_text="Indica se o cliente pode pedir troco (ex.: dinheiro)."
    )
    ativa = models.BooleanField("ativa", default=True)
    ordem = models.PositiveSmallIntegerField("ordem de exibição", default=0)

    class Meta:
        db_table = "sb_forma_pagamento"
        ordering = ["ordem", "nome"]
        verbose_name = "forma de pagamento"
        verbose_name_plural = "formas de pagamento"
        indexes = [models.Index(fields=["ativa", "ordem"], name="sb_forma_pag_ativa_ordem_idx")]

    def __str__(self) -> str:
        return self.nome

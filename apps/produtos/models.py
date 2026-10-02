"""Models do app ``produtos``.

O catálogo e o preço são únicos para a rede; a quantidade disponível em cada
filial fica no app ``estoque``. Valores monetários usam ``DecimalField`` (nunca ``float``).
"""

from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from apps.core.models import TimeStampedModel


class Categoria(models.TextChoices):
    """Seções do supermercado."""

    HORTIFRUTI = "HORTIFRUTI", "Hortifrúti"
    MERCEARIA = "MERCEARIA", "Mercearia"
    BEBIDAS = "BEBIDAS", "Bebidas"
    LATICINIOS = "LATICINIOS", "Laticínios e frios"
    PADARIA = "PADARIA", "Padaria"
    ACOUGUE = "ACOUGUE", "Açougue"
    LIMPEZA = "LIMPEZA", "Limpeza"
    HIGIENE = "HIGIENE", "Higiene e beleza"


class Produto(TimeStampedModel):
    """Produto vendido pela rede, identificado de forma única pelo SKU."""

    nome = models.CharField("nome", max_length=150)
    descricao = models.TextField("descrição", blank=True, default="")
    categoria = models.CharField("categoria", max_length=20, choices=Categoria.choices, default=Categoria.MERCEARIA)
    preco = models.DecimalField(
        "preço",
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    sku = models.CharField("SKU", max_length=30, unique=True)
    ativo = models.BooleanField("ativo", default=True)

    class Meta:
        db_table = "sb_produto"
        ordering = ["nome"]
        verbose_name = "produto"
        verbose_name_plural = "produtos"
        indexes = [
            models.Index(fields=["nome"], name="sb_produto_nome_idx"),
            models.Index(fields=["categoria", "ativo"], name="sb_produto_cat_ativo_idx"),
        ]
        constraints = [
            models.CheckConstraint(condition=models.Q(preco__gt=0), name="sb_produto_preco_positivo"),
        ]

    def __str__(self) -> str:
        return f"{self.nome} ({self.sku})"

"""Models do app ``pedidos``.

Fluxo de status do pedido::

    PENDENTE -> EM_SEPARACAO -> SEPARADO -> FINALIZADO
        \\____________\\_____________\\-----> CANCELADO

As transições permitidas ficam em ``TRANSICOES_PEDIDO`` e são aplicadas pelos
serviços de ``apps.pedidos.services``.
"""

import secrets
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from apps.core.models import TimeStampedModel


class StatusPedido(models.TextChoices):
    """Etapas do ciclo de vida de um pedido."""

    PENDENTE = "PENDENTE", "Pendente"
    EM_SEPARACAO = "EM_SEPARACAO", "Em separação"
    SEPARADO = "SEPARADO", "Separado"
    FINALIZADO = "FINALIZADO", "Finalizado"
    CANCELADO = "CANCELADO", "Cancelado"


TRANSICOES_PEDIDO: dict[str, frozenset[str]] = {
    StatusPedido.PENDENTE: frozenset({StatusPedido.EM_SEPARACAO, StatusPedido.CANCELADO}),
    StatusPedido.EM_SEPARACAO: frozenset({StatusPedido.SEPARADO, StatusPedido.CANCELADO}),
    StatusPedido.SEPARADO: frozenset({StatusPedido.FINALIZADO, StatusPedido.CANCELADO}),
    StatusPedido.FINALIZADO: frozenset(),
    StatusPedido.CANCELADO: frozenset(),
}


class StatusSeparacao(models.TextChoices):
    """Situação de uma separação."""

    EM_ANDAMENTO = "EM_ANDAMENTO", "Em andamento"
    CONCLUIDA = "CONCLUIDA", "Concluída"
    CANCELADA = "CANCELADA", "Cancelada"


def gerar_codigo_pedido() -> str:
    """Gera um código curto e não sequencial para o pedido (ex.: ``PED-4F9A1C2B``)."""
    return f"PED-{secrets.token_hex(4).upper()}"


class Pedido(TimeStampedModel):
    """Pedido de um cliente em uma filial."""

    codigo = models.CharField("código", max_length=20, unique=True, default=gerar_codigo_pedido)
    cliente = models.ForeignKey(
        "clientes.Cliente", verbose_name="cliente", on_delete=models.PROTECT, related_name="pedidos"
    )
    loja = models.ForeignKey("filiais.Loja", verbose_name="loja", on_delete=models.PROTECT, related_name="pedidos")
    status = models.CharField("status", max_length=20, choices=StatusPedido.choices, default=StatusPedido.PENDENTE)
    observacao = models.TextField("observação", blank=True, default="")

    class Meta:
        db_table = "sb_pedido"
        ordering = ["-data_criacao"]
        verbose_name = "pedido"
        verbose_name_plural = "pedidos"
        indexes = [
            models.Index(fields=["loja", "status"], name="sb_pedido_loja_status_idx"),
            models.Index(fields=["data_criacao"], name="sb_pedido_data_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.codigo} ({self.get_status_display()})"

    @property
    def total(self) -> Decimal:
        """Soma dos subtotais dos itens (use ``prefetch_related('itens')``)."""
        return sum((item.subtotal for item in self.itens.all()), Decimal("0.00"))

    def pode_mudar_para(self, novo_status: str) -> bool:
        """Indica se a transição de status é permitida."""
        return novo_status in TRANSICOES_PEDIDO[self.status]


class ItemPedido(models.Model):
    """Item de um pedido. O preço é congelado no momento da compra."""

    pedido = models.ForeignKey(Pedido, verbose_name="pedido", on_delete=models.CASCADE, related_name="itens")
    produto = models.ForeignKey(
        "produtos.Produto", verbose_name="produto", on_delete=models.PROTECT, related_name="itens_pedido"
    )
    quantidade = models.PositiveIntegerField("quantidade", validators=[MinValueValidator(1)])
    preco_unitario = models.DecimalField("preço unitário", max_digits=10, decimal_places=2)

    class Meta:
        db_table = "sb_item_pedido"
        ordering = ["pedido", "id"]
        verbose_name = "item do pedido"
        verbose_name_plural = "itens do pedido"
        constraints = [
            models.UniqueConstraint(fields=["pedido", "produto"], name="sb_item_pedido_produto_uniq"),
            models.CheckConstraint(condition=models.Q(quantidade__gt=0), name="sb_item_quantidade_positiva"),
            models.CheckConstraint(condition=models.Q(preco_unitario__gt=0), name="sb_item_preco_positivo"),
        ]

    def __str__(self) -> str:
        return f"{self.quantidade}x {self.produto.nome}"

    @property
    def subtotal(self) -> Decimal:
        """Quantidade multiplicada pelo preço unitário."""
        return self.preco_unitario * self.quantidade


class Separacao(models.Model):
    """Registro de um separador montando um pedido."""

    pedido = models.ForeignKey(Pedido, verbose_name="pedido", on_delete=models.CASCADE, related_name="separacoes")
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="separador",
        on_delete=models.PROTECT,
        related_name="separacoes",
    )
    status = models.CharField(
        "status", max_length=20, choices=StatusSeparacao.choices, default=StatusSeparacao.EM_ANDAMENTO
    )
    data_inicio = models.DateTimeField("início", default=timezone.now)
    data_conclusao = models.DateTimeField("conclusão", null=True, blank=True)

    class Meta:
        db_table = "sb_separacao"
        ordering = ["-data_inicio"]
        verbose_name = "separação"
        verbose_name_plural = "separações"
        constraints = [
            models.UniqueConstraint(
                fields=["pedido"],
                condition=models.Q(status=StatusSeparacao.EM_ANDAMENTO),
                name="sb_separacao_uma_ativa_por_pedido",
            ),
        ]

    def __str__(self) -> str:
        return f"Separação {self.pk} do {self.pedido.codigo}"

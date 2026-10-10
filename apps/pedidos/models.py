"""Models do app ``pedidos``.

Fluxo de status do pedido::

    PENDENTE -> EM_SEPARACAO -> SEPARADO -> [SAIU_PARA_ENTREGA] -> FINALIZADO
        \\____________\\_____________\\_______________\\-----> CANCELADO

``SAIU_PARA_ENTREGA`` só existe na entrega em domicílio, e nela é obrigatório:
o pedido de entrega não vai direto de SEPARADO para FINALIZADO, e o de
retirada na loja nunca sai para entrega.

As transições permitidas ficam em ``TRANSICOES_PEDIDO`` (mais a regra da forma
de entrega em ``Pedido.pode_mudar_para``) e são aplicadas pelos serviços de
``apps.pedidos.services``.
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
    SAIU_PARA_ENTREGA = "SAIU_PARA_ENTREGA", "Saiu para entrega"
    FINALIZADO = "FINALIZADO", "Finalizado"
    CANCELADO = "CANCELADO", "Cancelado"


TRANSICOES_PEDIDO: dict[str, frozenset[str]] = {
    StatusPedido.PENDENTE: frozenset({StatusPedido.EM_SEPARACAO, StatusPedido.CANCELADO}),
    StatusPedido.EM_SEPARACAO: frozenset({StatusPedido.SEPARADO, StatusPedido.CANCELADO}),
    StatusPedido.SEPARADO: frozenset({StatusPedido.SAIU_PARA_ENTREGA, StatusPedido.FINALIZADO, StatusPedido.CANCELADO}),
    StatusPedido.SAIU_PARA_ENTREGA: frozenset({StatusPedido.FINALIZADO, StatusPedido.CANCELADO}),
    StatusPedido.FINALIZADO: frozenset(),
    StatusPedido.CANCELADO: frozenset(),
}


class TipoEntrega(models.TextChoices):
    """Como o cliente recebe o pedido."""

    RETIRADA = "RETIRADA", "Retirada na loja"
    DOMICILIO = "DOMICILIO", "Entrega em domicílio"


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
    # Opcional no banco só por causa dos pedidos anteriores à forma de pagamento;
    # a API exige a forma de pagamento em todo pedido novo.
    forma_pagamento = models.ForeignKey(
        "pagamentos.FormaPagamento",
        verbose_name="forma de pagamento",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="pedidos",
    )
    tipo_entrega = models.CharField(
        "tipo de entrega", max_length=20, choices=TipoEntrega.choices, default=TipoEntrega.RETIRADA
    )
    # Cópia do endereço no momento da compra: editar ou excluir o endereço do
    # cliente depois não altera para onde o pedido foi entregue.
    endereco_entrega = models.TextField("endereço de entrega", blank=True, default="")
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
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(tipo_entrega=TipoEntrega.DOMICILIO) | ~models.Q(endereco_entrega=""),
                name="sb_pedido_domicilio_com_endereco",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.codigo} ({self.get_status_display()})"

    @property
    def total(self) -> Decimal:
        """Soma dos subtotais dos itens (use ``prefetch_related('itens')``)."""
        return sum((item.subtotal for item in self.itens.all()), Decimal("0.00"))

    def pode_mudar_para(self, novo_status: str) -> bool:
        """Indica se a transição de status é permitida para a forma de entrega do pedido."""
        if novo_status not in TRANSICOES_PEDIDO[self.status]:
            return False
        if self.status == StatusPedido.SEPARADO and novo_status != StatusPedido.CANCELADO:
            # Separado, o pedido de entrega sai para entrega; o de retirada é finalizado no caixa.
            domicilio = self.tipo_entrega == TipoEntrega.DOMICILIO
            return novo_status == (StatusPedido.SAIU_PARA_ENTREGA if domicilio else StatusPedido.FINALIZADO)
        return True


class ItemPedido(models.Model):
    """Item de um pedido. O preço é congelado no momento da compra."""

    pedido = models.ForeignKey(Pedido, verbose_name="pedido", on_delete=models.CASCADE, related_name="itens")
    produto = models.ForeignKey(
        "produtos.Produto", verbose_name="produto", on_delete=models.PROTECT, related_name="itens_pedido"
    )
    quantidade = models.PositiveIntegerField("quantidade", validators=[MinValueValidator(1)])
    preco_unitario = models.DecimalField("preço unitário", max_digits=10, decimal_places=2)
    # Checklist do separador: marcado quando o item já foi colocado no pedido.
    separado = models.BooleanField("separado", default=False)

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

"""Models do app ``estoque``."""

from django.db import models


class EstoqueLocal(models.Model):
    """Saldo de um produto em uma filial. Existe no máximo um por produto/filial."""

    produto = models.ForeignKey(
        "produtos.Produto", verbose_name="produto", on_delete=models.CASCADE, related_name="estoques"
    )
    loja = models.ForeignKey("filiais.Loja", verbose_name="loja", on_delete=models.CASCADE, related_name="estoques")
    quantidade = models.IntegerField("quantidade", default=0)
    quantidade_minima = models.IntegerField("quantidade mínima", default=0)
    data_atualizacao = models.DateTimeField("data de atualização", auto_now=True)

    class Meta:
        db_table = "sb_estoque_local"
        ordering = ["loja", "produto"]
        verbose_name = "estoque local"
        verbose_name_plural = "estoques locais"
        constraints = [
            models.UniqueConstraint(fields=["produto", "loja"], name="sb_estoque_produto_loja_uniq"),
            models.CheckConstraint(condition=models.Q(quantidade__gte=0), name="sb_estoque_quantidade_nao_negativa"),
            models.CheckConstraint(condition=models.Q(quantidade_minima__gte=0), name="sb_estoque_minimo_nao_negativo"),
        ]
        indexes = [models.Index(fields=["loja", "quantidade"], name="sb_estoque_loja_qtd_idx")]

    def __str__(self) -> str:
        return f"{self.produto} @ {self.loja}: {self.quantidade}"

    @property
    def abaixo_do_minimo(self) -> bool:
        """Indica se o saldo está igual ou abaixo da quantidade mínima."""
        return self.quantidade <= self.quantidade_minima

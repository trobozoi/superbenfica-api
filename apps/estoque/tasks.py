"""Tasks Celery do app ``estoque``."""

import logging
from collections import defaultdict

from celery import shared_task
from django.db.models import F

from apps.core.realtime import notificar_loja
from apps.estoque.models import EstoqueLocal

logger = logging.getLogger(__name__)

EVENTO_ESTOQUE_BAIXO = "estoque.abaixo_do_minimo"


@shared_task
def verificar_estoque_minimo() -> int:
    """Notifica cada filial sobre os produtos com saldo abaixo do mínimo.

    Executada periodicamente pelo Celery Beat (ver ``CELERY_BEAT_SCHEDULE``).

    Returns:
        Quantidade total de itens abaixo do mínimo encontrados.
    """
    itens = (
        EstoqueLocal.objects.filter(quantidade__lte=F("quantidade_minima"), produto__ativo=True)
        .select_related("produto")
        .order_by("loja_id", "produto__nome")
    )
    por_loja: dict[int, list[dict]] = defaultdict(list)
    for estoque in itens:
        por_loja[estoque.loja_id].append(
            {
                "produto_id": estoque.produto_id,
                "produto": estoque.produto.nome,
                "quantidade": estoque.quantidade,
                "quantidade_minima": estoque.quantidade_minima,
            }
        )
    for loja_id, produtos in por_loja.items():
        notificar_loja(loja_id, EVENTO_ESTOQUE_BAIXO, {"produtos": produtos})
    total = sum(len(produtos) for produtos in por_loja.values())
    logger.info("Verificação de estoque mínimo: %s itens em %s filiais.", total, len(por_loja))
    return total

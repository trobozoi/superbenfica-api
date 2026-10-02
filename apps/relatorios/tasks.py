"""Tasks Celery do app ``relatorios``."""

import logging
from datetime import timedelta
from typing import Any

from celery import shared_task
from django.core.cache import cache
from django.utils import timezone

from apps.relatorios import services

logger = logging.getLogger(__name__)

CACHE_RESUMO_DIARIO_SEGUNDOS = 60 * 60 * 24 * 7


@shared_task
def gerar_resumo_diario() -> dict[str, Any]:
    """Calcula as vendas do dia anterior e guarda o resumo em cache por 7 dias.

    Executada diariamente pelo Celery Beat. A chave do cache é
    ``relatorios:resumo:<AAAA-MM-DD>``.
    """
    ontem = timezone.localdate() - timedelta(days=1)
    resumo = {
        "data": ontem.isoformat(),
        "vendas": services.vendas_por_loja(None, ontem, ontem),
        "pedidos_por_status": services.pedidos_por_status(None, ontem, ontem),
    }
    cache.set(f"relatorios:resumo:{ontem.isoformat()}", resumo, CACHE_RESUMO_DIARIO_SEGUNDOS)
    logger.info("Resumo diário de %s gerado para %s filiais.", ontem, len(resumo["vendas"]))
    # O retorno vai para o result backend em JSON: apenas tipos simples.
    return {"data": resumo["data"], "filiais": len(resumo["vendas"])}

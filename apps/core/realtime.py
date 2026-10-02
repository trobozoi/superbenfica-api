"""Publicação de eventos em tempo real via Django Channels.

Os eventos são enviados somente após o commit da transação
(``transaction.on_commit``), para que os clientes nunca recebam dados de uma
operação que foi desfeita. Falhas de conexão com o Redis são registradas em
log e não interrompem a requisição.
"""

import logging
from typing import Any

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)

TIPO_MENSAGEM = "evento.notificacao"


def grupo_loja(loja_id: int) -> str:
    """Nome do grupo Channels que recebe os eventos de uma filial."""
    return f"loja_{loja_id}"


def grupo_usuario(usuario_id: int) -> str:
    """Nome do grupo Channels que recebe os eventos de um usuário."""
    return f"usuario_{usuario_id}"


def _enviar(grupo: str, evento: str, dados: dict[str, Any]) -> None:
    """Envia a mensagem ao grupo, registrando falhas de infraestrutura."""
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return
    mensagem = {"type": TIPO_MENSAGEM, "evento": evento, "dados": dados}
    try:
        async_to_sync(channel_layer.group_send)(grupo, mensagem)
    except (OSError, RedisError):
        logger.exception("Falha ao publicar o evento %s no grupo %s", evento, grupo)


def publicar(grupo: str, evento: str, dados: dict[str, Any]) -> None:
    """Agenda a publicação do evento para depois do commit da transação."""
    transaction.on_commit(lambda: _enviar(grupo, evento, dados))


def notificar_loja(loja_id: int, evento: str, dados: dict[str, Any]) -> None:
    """Publica um evento para todos os funcionários conectados da filial."""
    publicar(grupo_loja(loja_id), evento, dados)


def notificar_usuario(usuario_id: int, evento: str, dados: dict[str, Any]) -> None:
    """Publica um evento para um usuário específico (ex.: o cliente do pedido)."""
    publicar(grupo_usuario(usuario_id), evento, dados)

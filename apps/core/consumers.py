"""Consumers WebSocket (Django Channels).

- ``LojaConsumer``: funcionários acompanham pedidos e estoque da filial.
- ``NotificacoesUsuarioConsumer``: cada usuário recebe eventos próprios
  (ex.: o cliente acompanha o status dos seus pedidos).

Mensagens enviadas ao cliente têm o formato ``{"evento": str, "dados": dict}``.
O cliente pode enviar ``{"acao": "ping"}`` para checar a conexão.
"""

from typing import Any

from channels.generic.websocket import AsyncJsonWebsocketConsumer

from apps.core.constants import ROLES_EQUIPE, Role
from apps.core.realtime import grupo_loja, grupo_usuario

CODIGO_NAO_AUTORIZADO = 4401
CODIGO_PROIBIDO = 4403


def pode_acompanhar_loja(user: Any, loja_id: int) -> bool:
    """Admins acompanham qualquer filial; funcionários, apenas a própria."""
    if user.is_superuser or user.role == Role.ADMIN:
        return True
    return user.role in ROLES_EQUIPE and user.loja_id == loja_id


class BaseNotificacaoConsumer(AsyncJsonWebsocketConsumer):
    """Comportamento comum: entrada/saída do grupo e repasse de eventos."""

    grupo: str | None = None

    async def entrar_no_grupo(self, grupo: str) -> None:
        """Inscreve a conexão no grupo e aceita o handshake."""
        self.grupo = grupo
        await self.channel_layer.group_add(grupo, self.channel_name)
        await self.accept()

    async def disconnect(self, code: int) -> None:
        """Remove a conexão do grupo ao desconectar."""
        if self.grupo:
            await self.channel_layer.group_discard(self.grupo, self.channel_name)

    async def receive_json(self, content: Any, **kwargs: Any) -> None:
        """Responde ao ``ping`` do cliente; demais mensagens são ignoradas."""
        if isinstance(content, dict) and content.get("acao") == "ping":
            await self.send_json({"evento": "pong", "dados": {}})

    async def evento_notificacao(self, event: dict[str, Any]) -> None:
        """Repassa ao cliente os eventos publicados por ``apps.core.realtime``."""
        await self.send_json({"evento": event["evento"], "dados": event["dados"]})


class LojaConsumer(BaseNotificacaoConsumer):
    """Canal ``/ws/lojas/<loja_id>/`` para a equipe da filial."""

    async def connect(self) -> None:
        """Aceita apenas funcionários autenticados da filial (ou admins)."""
        user = self.scope.get("user")
        if user is None or not user.is_authenticated:
            await self.close(code=CODIGO_NAO_AUTORIZADO)
            return
        loja_id = int(self.scope["url_route"]["kwargs"]["loja_id"])
        if not pode_acompanhar_loja(user, loja_id):
            await self.close(code=CODIGO_PROIBIDO)
            return
        await self.entrar_no_grupo(grupo_loja(loja_id))


class NotificacoesUsuarioConsumer(BaseNotificacaoConsumer):
    """Canal ``/ws/notificacoes/`` com os eventos do próprio usuário."""

    async def connect(self) -> None:
        """Aceita qualquer usuário autenticado."""
        user = self.scope.get("user")
        if user is None or not user.is_authenticated:
            await self.close(code=CODIGO_NAO_AUTORIZADO)
            return
        await self.entrar_no_grupo(grupo_usuario(user.pk))

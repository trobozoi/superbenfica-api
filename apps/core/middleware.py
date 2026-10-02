"""Middleware de autenticação JWT para conexões WebSocket.

O navegador não permite cabeçalhos customizados no handshake do WebSocket,
então o token de acesso é enviado na query string: ``?token=<access>``.
Em produção use sempre ``wss://`` para que o token trafegue criptografado.
"""

from typing import Any
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken


@database_sync_to_async
def usuario_do_token(token: str) -> Any:
    """Valida o token de acesso e retorna o usuário ativo correspondente.

    Retorna ``AnonymousUser`` se o token for inválido, expirado ou se o
    usuário não existir/estiver inativo.
    """
    user_model = get_user_model()
    try:
        access = AccessToken(token)
        return user_model.objects.get(pk=access["user_id"], is_active=True)
    except (TokenError, KeyError, user_model.DoesNotExist):
        return AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):
    """Preenche ``scope["user"]`` a partir do parâmetro ``token`` da URL."""

    async def __call__(self, scope: dict, receive: Any, send: Any) -> Any:
        """Autentica a conexão antes de repassá-la ao roteador."""
        query = parse_qs(scope.get("query_string", b"").decode())
        token = query.get("token", [""])[0]
        scope["user"] = await usuario_do_token(token) if token else AnonymousUser()
        return await super().__call__(scope, receive, send)

"""Rotas WebSocket do projeto (usadas em ``config.asgi``)."""

from django.urls import path

from apps.core.consumers import LojaConsumer, NotificacoesUsuarioConsumer

websocket_urlpatterns = [
    path("ws/lojas/<int:loja_id>/", LojaConsumer.as_asgi()),
    path("ws/notificacoes/", NotificacoesUsuarioConsumer.as_asgi()),
]

"""Testes dos consumers WebSocket (Django Channels)."""

import pytest
from asgiref.sync import async_to_sync, sync_to_async
from channels.testing import WebsocketCommunicator
from rest_framework_simplejwt.tokens import AccessToken

from apps.core.realtime import notificar_loja
from config.asgi import application

pytestmark = pytest.mark.django_db(transaction=True)

ORIGEM = [(b"origin", b"http://localhost")]


def conectar(caminho: str, usuario=None):
    """Cria o comunicador, com token JWT na query string se houver usuário."""
    if usuario is not None:
        caminho = f"{caminho}?token={AccessToken.for_user(usuario)}"
    return WebsocketCommunicator(application, caminho, headers=ORIGEM)


async def _abrir(communicator: WebsocketCommunicator):
    conectado, codigo = await communicator.connect()
    return conectado, codigo


def test_anonimo_e_recusado(loja):
    async def cenario():
        communicator = conectar(f"/ws/lojas/{loja.pk}/")
        conectado, codigo = await _abrir(communicator)
        assert not conectado
        assert codigo == 4401
        notificacoes = conectar("/ws/notificacoes/")
        assert not (await _abrir(notificacoes))[0]

    async_to_sync(cenario)()


def test_token_invalido_e_recusado(loja):
    async def cenario():
        communicator = WebsocketCommunicator(application, f"/ws/lojas/{loja.pk}/?token=invalido", headers=ORIGEM)
        assert not (await communicator.connect())[0]

    async_to_sync(cenario)()


def test_funcionario_de_outra_filial_e_recusado(separador, outra_loja):
    async def cenario():
        conectado, codigo = await _abrir(conectar(f"/ws/lojas/{outra_loja.pk}/", separador))
        assert not conectado
        assert codigo == 4403

    async_to_sync(cenario)()


def test_funcionario_recebe_eventos_da_filial(separador, loja):
    async def cenario():
        communicator = conectar(f"/ws/lojas/{loja.pk}/", separador)
        assert (await communicator.connect())[0]
        await communicator.send_json_to({"acao": "ping"})
        assert await communicator.receive_json_from() == {"evento": "pong", "dados": {}}
        await communicator.disconnect()

    async_to_sync(cenario)()


def test_evento_publicado_chega_ao_admin(admin, loja):
    async def cenario():
        communicator = conectar(f"/ws/lojas/{loja.pk}/", admin)
        assert (await communicator.connect())[0]
        await sync_to_async(notificar_loja)(loja.pk, "teste.evento", {"ok": True})
        assert await communicator.receive_json_from(timeout=2) == {"evento": "teste.evento", "dados": {"ok": True}}
        await communicator.disconnect()

    async_to_sync(cenario)()


def test_cliente_conecta_nas_notificacoes(usuario_cliente):
    async def cenario():
        communicator = conectar("/ws/notificacoes/", usuario_cliente)
        assert (await communicator.connect())[0]
        await communicator.send_json_to({"acao": "outra"})
        assert await communicator.receive_nothing()
        await communicator.disconnect()

    async_to_sync(cenario)()

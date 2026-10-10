"""Testes do rate limit por endpoint.

O settings de teste desliga os throttles globais para não interferir nos
demais testes; aqui eles são religados só nas views testadas.
"""

import pytest
from django.conf import settings
from django.core.cache import cache
from rest_framework.throttling import ScopedRateThrottle

from apps.core.throttling import Escopo
from apps.estoque.views import EstoqueLocalViewSet
from apps.pedidos.views import PedidoViewSet, SeparacaoViewSet
from apps.produtos.views import ProdutoViewSet
from apps.relatorios.views import RelatorioBaseView
from apps.usuarios.views import LoginView, RegistroClienteView

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def limpar_cache():
    """Zera as contagens de requisições entre os testes."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def limites(monkeypatch):
    """Liga o ScopedRateThrottle em uma view e define limites baixos para o teste."""

    def _ligar(view, **taxas: str) -> None:
        monkeypatch.setattr(view, "throttle_classes", [ScopedRateThrottle])
        monkeypatch.setattr(ScopedRateThrottle, "THROTTLE_RATES", {**ScopedRateThrottle.THROTTLE_RATES, **taxas})

    return _ligar


def test_todo_escopo_usado_tem_limite_configurado():
    escopos = {valor for nome, valor in vars(Escopo).items() if nome.isupper()}
    assert escopos <= set(settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"])


def test_views_declaram_os_escopos():
    assert LoginView.throttle_scope == Escopo.LOGIN
    assert RegistroClienteView.throttle_scope == Escopo.REGISTRO
    assert RelatorioBaseView.throttle_scope == Escopo.RELATORIOS
    assert PedidoViewSet.throttle_scopes_por_acao["create"] == Escopo.PEDIDOS_CRIACAO
    assert SeparacaoViewSet.throttle_scopes_por_acao["concluir"] == Escopo.PEDIDOS_FLUXO
    assert EstoqueLocalViewSet.throttle_scopes_por_acao["ajustar"] == Escopo.ESTOQUE_AJUSTE
    assert ProdutoViewSet.throttle_scopes_por_acao["foto"] == Escopo.UPLOAD


def test_login_bloqueia_apos_o_limite(api, limites, gerente):
    limites(LoginView)
    dados = {"email": gerente.email, "password": "senha-errada"}
    respostas = [api().post("/api/auth/token/", dados) for _ in range(6)]
    assert [r.status_code for r in respostas[:5]] == [401] * 5
    assert respostas[5].status_code == 429
    assert int(respostas[5]["Retry-After"]) > 0


def test_limite_vale_so_para_a_acao_configurada(api, limites, usuario_cliente, loja, estoque, produto, forma_pagamento):
    limites(PedidoViewSet, pedidos_criacao="2/min")
    pedido = {
        "loja": loja.pk,
        "forma_pagamento": forma_pagamento.pk,
        "itens": [{"produto": produto.pk, "quantidade": 1}],
    }
    criacoes = [api(usuario_cliente).post("/api/pedidos/", pedido, format="json").status_code for _ in range(3)]
    assert criacoes == [201, 201, 429]
    listagens = [api(usuario_cliente).get("/api/pedidos/").status_code for _ in range(5)]
    assert listagens == [200] * 5


def test_limite_e_por_usuario(api, limites, gerente, criar_usuario, loja):
    limites(RelatorioBaseView, relatorios="1/min")
    outro_gerente = criar_usuario("GERENTE", email="gerente2@teste.com")
    assert api(gerente).get("/api/relatorios/vendas/").status_code == 200
    assert api(gerente).get("/api/relatorios/vendas/").status_code == 429
    assert api(outro_gerente).get("/api/relatorios/vendas/").status_code == 200

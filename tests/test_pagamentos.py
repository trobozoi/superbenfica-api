"""Testes das formas de pagamento e do vínculo com o pedido."""

import pytest
from django.core.management import call_command
from django.db.models import ProtectedError

from apps.pagamentos.models import FormaPagamento, TipoPagamento
from apps.pedidos.models import Pedido

pytestmark = pytest.mark.django_db

URL = "/api/formas-pagamento/"


def test_migration_cadastra_as_cinco_formas():
    formas = {forma.tipo: forma for forma in FormaPagamento.objects.all()}
    assert set(formas) == set(TipoPagamento.values)
    assert formas[TipoPagamento.DINHEIRO].permite_troco
    assert not formas[TipoPagamento.PIX].permite_troco
    assert str(formas[TipoPagamento.VALE_ALIMENTACAO]) == "Vale-alimentação"


def test_listagem_ordenada_e_cliente_ve_somente_ativas(api, usuario_cliente, caixa):
    FormaPagamento.objects.filter(tipo=TipoPagamento.DEBITO).update(ativa=False)
    nomes_cliente = [f["nome"] for f in api(usuario_cliente).get(URL).data["results"]]
    assert nomes_cliente == ["Pix", "Cartão de crédito", "Dinheiro", "Vale-alimentação"]
    assert api(caixa).get(URL).data["count"] == 5


def test_somente_admin_cadastra(api, admin, gerente):
    dados = {"nome": " Vale-refeição ", "tipo": TipoPagamento.VALE_ALIMENTACAO, "ordem": 6}
    assert api(gerente).post(URL, dados).status_code == 403
    resposta = api(admin).post(URL, dados)
    assert resposta.status_code == 201, resposta.data
    assert resposta.data["nome"] == "Vale-refeição"
    assert resposta.data["tipo_display"] == "Vale-alimentação"


def test_nome_unico_e_tipo_valido(api, admin):
    assert api(admin).post(URL, {"nome": "Pix", "tipo": TipoPagamento.PIX}).status_code == 400
    assert api(admin).post(URL, {"nome": "Boleto", "tipo": "BOLETO"}).status_code == 400


def test_excluir_desativa(api, admin, forma_pagamento):
    assert api(admin).delete(f"{URL}{forma_pagamento.pk}/").status_code == 204
    forma_pagamento.refresh_from_db()
    assert not forma_pagamento.ativa


@pytest.fixture
def dados_pedido(loja, estoque, produto, forma_pagamento):
    """Corpo válido para criar um pedido como cliente."""
    return {"loja": loja.pk, "forma_pagamento": forma_pagamento.pk, "itens": [{"produto": produto.pk, "quantidade": 1}]}


def test_pedido_grava_e_exibe_forma_de_pagamento(api, usuario_cliente, dados_pedido):
    resposta = api(usuario_cliente).post("/api/pedidos/", dados_pedido, format="json")
    assert resposta.status_code == 201, resposta.data
    assert resposta.data["forma_pagamento"] == dados_pedido["forma_pagamento"]
    assert resposta.data["forma_pagamento_nome"] == "Pix"


def test_pedido_exige_forma_de_pagamento(api, usuario_cliente, dados_pedido):
    dados_pedido.pop("forma_pagamento")
    resposta = api(usuario_cliente).post("/api/pedidos/", dados_pedido, format="json")
    assert resposta.status_code == 400
    assert "forma_pagamento" in resposta.data


def test_pedido_rejeita_forma_inativa(api, usuario_cliente, dados_pedido, forma_pagamento):
    forma_pagamento.ativa = False
    forma_pagamento.save()
    resposta = api(usuario_cliente).post("/api/pedidos/", dados_pedido, format="json")
    assert resposta.status_code == 400
    assert "forma_pagamento" in resposta.data


def test_forma_em_uso_nao_pode_ser_apagada_do_banco(api, usuario_cliente, dados_pedido, forma_pagamento):
    api(usuario_cliente).post("/api/pedidos/", dados_pedido, format="json")
    with pytest.raises(ProtectedError):
        forma_pagamento.delete()


def test_filtrar_pedidos_por_forma_de_pagamento(api, usuario_cliente, dados_pedido, admin):
    api(usuario_cliente).post("/api/pedidos/", dados_pedido, format="json")
    dinheiro = FormaPagamento.objects.get(tipo=TipoPagamento.DINHEIRO)
    assert api(admin).get("/api/pedidos/", {"forma_pagamento": dados_pedido["forma_pagamento"]}).data["count"] == 1
    assert api(admin).get("/api/pedidos/", {"forma_pagamento": dinheiro.pk}).data["count"] == 0


def test_carga_inicial_usa_formas_de_pagamento(monkeypatch):
    monkeypatch.setenv("DJANGO_SUPERUSER_EMAIL", "root@teste.com")
    monkeypatch.setenv("DJANGO_SUPERUSER_PASSWORD", "Senha-root-de-teste-1")
    monkeypatch.setenv("SEED_DEFAULT_PASSWORD", "Senha-seed-de-teste-1")
    call_command("carga_inicial", verbosity=0)
    tipos = dict(Pedido.objects.values_list("codigo", "forma_pagamento__tipo"))
    assert tipos["SEED-0001"] == TipoPagamento.PIX
    assert tipos["SEED-0003"] == TipoPagamento.DINHEIRO
    assert None not in tipos.values()

"""Testes de estoque por filial."""

import pytest

from apps.estoque.models import EstoqueLocal
from apps.estoque.tasks import verificar_estoque_minimo

pytestmark = pytest.mark.django_db


def test_funcionario_ve_somente_estoque_da_sua_filial(api, separador, estoque, produto, outra_loja):
    EstoqueLocal.objects.create(produto=produto, loja=outra_loja, quantidade=1)
    resposta = api(separador).get("/api/estoques/")
    assert resposta.status_code == 200
    assert [e["id"] for e in resposta.data["results"]] == [estoque.pk]


def test_admin_ve_todas_as_filiais(api, admin, estoque, produto, outra_loja):
    EstoqueLocal.objects.create(produto=produto, loja=outra_loja, quantidade=1)
    assert api(admin).get("/api/estoques/").data["count"] == 2


def test_cliente_nao_ve_estoque(api, usuario_cliente, estoque):
    assert api(usuario_cliente).get("/api/estoques/").status_code == 403


def test_filtro_abaixo_do_minimo(api, gerente, estoque, estoque_2):
    estoque_2.quantidade = 1
    estoque_2.save()
    abaixo = api(gerente).get("/api/estoques/", {"abaixo_do_minimo": "true"}).data["results"]
    acima = api(gerente).get("/api/estoques/", {"abaixo_do_minimo": "false"}).data["results"]
    assert [e["id"] for e in abaixo] == [estoque_2.pk]
    assert [e["id"] for e in acima] == [estoque.pk]


def test_gerente_cadastra_estoque_somente_na_sua_filial(api, gerente, produto, loja, outra_loja):
    dados = {"produto": produto.pk, "quantidade": 5, "quantidade_minima": 1}
    assert api(gerente).post("/api/estoques/", {**dados, "loja": outra_loja.pk}).status_code == 403
    assert api(gerente).post("/api/estoques/", {**dados, "loja": loja.pk}).status_code == 201


def test_estoque_nao_aceita_negativo(api, gerente, produto, loja):
    resposta = api(gerente).post(
        "/api/estoques/", {"produto": produto.pk, "loja": loja.pk, "quantidade": -1, "quantidade_minima": -1}
    )
    assert resposta.status_code == 400
    assert {"quantidade", "quantidade_minima"} <= set(resposta.data)


def test_ajuste_de_estoque(api, gerente, estoque):
    url = f"/api/estoques/{estoque.pk}/ajustar/"
    entrada = api(gerente).post(url, {"delta": 5, "motivo": "Recebimento"})
    assert entrada.status_code == 200
    assert entrada.data["quantidade"] == 15
    saida_excessiva = api(gerente).post(url, {"delta": -100, "motivo": "Perda"})
    assert saida_excessiva.status_code == 409
    zero = api(gerente).post(url, {"delta": 0, "motivo": "Nada"})
    assert zero.status_code == 400


def test_task_verificar_estoque_minimo(estoque, estoque_2):
    estoque_2.quantidade = 0
    estoque_2.save()
    assert verificar_estoque_minimo.delay().get() == 1

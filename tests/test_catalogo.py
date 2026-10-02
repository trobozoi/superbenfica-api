"""Testes de filiais e produtos."""

import pytest

from apps.produtos.models import Produto

pytestmark = pytest.mark.django_db

LOJA_NOVA = {
    "nome": "Loja Nova",
    "endereco": "Rua C, 3",
    "horario_abertura": "07:00",
    "horario_fechamento": "22:00",
}


def test_qualquer_autenticado_lista_lojas(api, usuario_cliente, loja):
    resposta = api(usuario_cliente).get("/api/lojas/")
    assert resposta.status_code == 200
    assert resposta.data["count"] == 1


def test_somente_admin_cria_loja(api, admin, gerente):
    assert api(gerente).post("/api/lojas/", LOJA_NOVA).status_code == 403
    assert api(admin).post("/api/lojas/", LOJA_NOVA).status_code == 201


def test_loja_horarios_iguais_invalidos(api, admin):
    resposta = api(admin).post("/api/lojas/", {**LOJA_NOVA, "horario_fechamento": "07:00"})
    assert resposta.status_code == 400


def test_excluir_loja_desativa(api, admin, loja):
    assert api(admin).delete(f"/api/lojas/{loja.pk}/").status_code == 204
    loja.refresh_from_db()
    assert not loja.ativa


def test_gerente_cria_produto_com_sku_normalizado(api, gerente):
    dados = {"nome": "Café", "sku": " cfe-1 ", "preco": "18.90", "categoria": "MERCEARIA"}
    resposta = api(gerente).post("/api/produtos/", dados)
    assert resposta.status_code == 201, resposta.data
    assert resposta.data["sku"] == "CFE-1"


def test_caixa_nao_cria_produto(api, caixa):
    assert api(caixa).post("/api/produtos/", {"nome": "X", "sku": "X", "preco": "1"}).status_code == 403


def test_cliente_ve_somente_produtos_ativos(api, usuario_cliente, gerente, produto, produto_2):
    api(gerente).delete(f"/api/produtos/{produto_2.pk}/")
    assert not Produto.objects.get(pk=produto_2.pk).ativo
    skus_cliente = {p["sku"] for p in api(usuario_cliente).get("/api/produtos/").data["results"]}
    skus_gerente = {p["sku"] for p in api(gerente).get("/api/produtos/").data["results"]}
    assert skus_cliente == {produto.sku}
    assert skus_gerente == {produto.sku, produto_2.sku}


def test_busca_de_produto(api, caixa, produto, produto_2):
    resposta = api(caixa).get("/api/produtos/", {"search": "feij"})
    assert [p["sku"] for p in resposta.data["results"]] == [produto_2.sku]

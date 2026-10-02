"""Testes de clientes e endereços."""

import pytest

from apps.clientes.models import Cliente

pytestmark = pytest.mark.django_db

ENDERECO = {
    "endereco": "Rua Teste",
    "numero": "10",
    "bairro": "Centro",
    "cidade": "Fortaleza",
    "estado": "CE",
    "cep": "60000000",
}


def test_cliente_ve_somente_o_proprio_cadastro(api, usuario_cliente, cliente):
    Cliente.objects.create(nome="Outro", email="outro@teste.com")
    resposta = api(usuario_cliente).get("/api/clientes/")
    assert [c["id"] for c in resposta.data["results"]] == [cliente.pk]


def test_funcionario_ve_todos(api, caixa, cliente):
    Cliente.objects.create(nome="Outro", email="outro@teste.com")
    assert api(caixa).get("/api/clientes/").data["count"] == 2


def test_caixa_cadastra_cliente_e_cliente_nao(api, caixa, usuario_cliente):
    dados = {"nome": "Balcão", "email": "BALCAO@teste.com"}
    assert api(usuario_cliente).post("/api/clientes/", dados).status_code == 403
    resposta = api(caixa).post("/api/clientes/", dados)
    assert resposta.status_code == 201
    assert resposta.data["email"] == "balcao@teste.com"


def test_atualizar_cliente_sincroniza_usuario(api, usuario_cliente, cliente):
    resposta = api(usuario_cliente).patch(f"/api/clientes/{cliente.pk}/", {"nome": "Nome Novo"})
    assert resposta.status_code == 200
    usuario_cliente.refresh_from_db()
    assert usuario_cliente.nome == "Nome Novo"


def test_cliente_cadastra_endereco_proprio(api, usuario_cliente, cliente):
    resposta = api(usuario_cliente).post("/api/enderecos/", {**ENDERECO, "cliente": cliente.pk})
    assert resposta.status_code == 201, resposta.data
    assert resposta.data["cep"] == "60000-000"
    assert api(usuario_cliente).get("/api/enderecos/").data["count"] == 1


def test_cliente_nao_cadastra_endereco_de_outro(api, usuario_cliente):
    outro = Cliente.objects.create(nome="Outro", email="outro@teste.com")
    resposta = api(usuario_cliente).post("/api/enderecos/", {**ENDERECO, "cliente": outro.pk})
    assert resposta.status_code == 400


def test_cep_invalido(api, caixa, cliente):
    resposta = api(caixa).post("/api/enderecos/", {**ENDERECO, "cliente": cliente.pk, "cep": "123"})
    assert resposta.status_code == 400


def test_funcionario_lista_enderecos(api, caixa, cliente):
    api(caixa).post("/api/enderecos/", {**ENDERECO, "cliente": cliente.pk})
    assert api(caixa).get("/api/enderecos/").data["count"] == 1

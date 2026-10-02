"""Testes de autenticação JWT, autocadastro e gestão de usuários."""

import pytest
from rest_framework_simplejwt.tokens import AccessToken

from apps.core.constants import Role
from apps.usuarios.models import Usuario
from tests.conftest import SENHA_TESTE

pytestmark = pytest.mark.django_db


def test_login_retorna_tokens_com_perfil(api, gerente):
    resposta = api().post("/api/auth/token/", {"email": gerente.email, "password": SENHA_TESTE})
    assert resposta.status_code == 200
    token = AccessToken(resposta.data["access"])
    assert token["role"] == Role.GERENTE
    assert token["loja_id"] == gerente.loja_id


def test_login_invalido(api, gerente):
    resposta = api().post("/api/auth/token/", {"email": gerente.email, "password": "errada"})
    assert resposta.status_code == 401


def test_refresh_e_logout(api, caixa):
    tokens = api().post("/api/auth/token/", {"email": caixa.email, "password": SENHA_TESTE}).data
    renovado = api().post("/api/auth/token/refresh/", {"refresh": tokens["refresh"]})
    assert renovado.status_code == 200
    assert api().post("/api/auth/token/verify/", {"token": renovado.data["access"]}).status_code == 200
    assert api().post("/api/auth/logout/", {"refresh": renovado.data["refresh"]}).status_code == 200
    assert api().post("/api/auth/token/refresh/", {"refresh": renovado.data["refresh"]}).status_code == 401


def test_registro_de_cliente(api, loja):
    dados = {"nome": "Nova Cliente", "email": "Nova@Cliente.com", "password": "Uma-senha-forte-9", "loja": loja.pk}
    resposta = api().post("/api/auth/registrar/", dados)
    assert resposta.status_code == 201, resposta.data
    usuario = Usuario.objects.get(email="nova@cliente.com")
    assert usuario.role == Role.CLIENTE
    assert usuario.cliente.loja == loja
    repetido = api().post("/api/auth/registrar/", dados)
    assert repetido.status_code == 400


def test_registro_rejeita_senha_fraca(api):
    resposta = api().post("/api/auth/registrar/", {"nome": "X", "email": "x@x.com", "password": "123"})
    assert resposta.status_code == 400
    assert "password" in resposta.data


def test_me(api, separador):
    resposta = api(separador).get("/api/usuarios/me/")
    assert resposta.status_code == 200
    assert resposta.data["email"] == separador.email


def test_gerente_lista_apenas_sua_filial(api, gerente, criar_usuario, outra_loja):
    criar_usuario(Role.CAIXA, loja_usuario=outra_loja, email="caixa2@teste.com")
    emails = {u["email"] for u in api(gerente).get("/api/usuarios/").data["results"]}
    assert gerente.email in emails
    assert "caixa2@teste.com" not in emails


def test_gerente_nao_cria_admin_nem_em_outra_filial(api, gerente, outra_loja):
    base = {"nome": "Novo", "password": "Uma-senha-forte-9", "loja": gerente.loja_id}
    admin = api(gerente).post("/api/usuarios/", {**base, "email": "a@a.com", "role": Role.ADMIN})
    assert admin.status_code == 400
    outra = api(gerente).post("/api/usuarios/", {**base, "email": "b@b.com", "role": Role.CAIXA, "loja": outra_loja.pk})
    assert outra.status_code == 400
    ok = api(gerente).post("/api/usuarios/", {**base, "email": "c@c.com", "role": Role.CAIXA})
    assert ok.status_code == 201, ok.data
    assert "password" not in ok.data


def test_admin_desativa_usuario(api, admin, caixa):
    assert api(admin).delete(f"/api/usuarios/{caixa.pk}/").status_code == 204
    caixa.refresh_from_db()
    assert not caixa.is_active


def test_caixa_nao_gerencia_usuarios(api, caixa):
    assert api(caixa).get("/api/usuarios/").status_code == 403
    assert api().get("/api/usuarios/").status_code == 401

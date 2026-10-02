"""Testes do fluxo de pedidos e separação."""

import pytest

from apps.clientes.models import Cliente
from apps.pedidos.models import Pedido, StatusPedido, StatusSeparacao

pytestmark = pytest.mark.django_db


@pytest.fixture
def pedido_criado(api, usuario_cliente, loja, estoque, estoque_2, produto, produto_2):
    """Pedido de 2x produto + 1x produto_2 feito pelo cliente."""
    resposta = api(usuario_cliente).post(
        "/api/pedidos/",
        {
            "loja": loja.pk,
            "itens": [
                {"produto": produto.pk, "quantidade": 1},
                {"produto": produto_2.pk, "quantidade": 1},
                {"produto": produto.pk, "quantidade": 1},
            ],
        },
        format="json",
    )
    assert resposta.status_code == 201, resposta.data
    return Pedido.objects.get(pk=resposta.data["id"])


def test_criar_pedido_baixa_estoque_e_soma_itens(pedido_criado, estoque, estoque_2):
    estoque.refresh_from_db()
    estoque_2.refresh_from_db()
    assert estoque.quantidade == 8
    assert estoque_2.quantidade == 4
    assert pedido_criado.itens.count() == 2
    assert str(pedido_criado.total) == "58.50"


def test_estoque_insuficiente_retorna_409(api, caixa, cliente, loja, estoque, produto):
    resposta = api(caixa).post(
        "/api/pedidos/",
        {"cliente": cliente.pk, "loja": loja.pk, "itens": [{"produto": produto.pk, "quantidade": 11}]},
        format="json",
    )
    assert resposta.status_code == 409
    estoque.refresh_from_db()
    assert estoque.quantidade == 10


def test_produto_sem_estoque_na_filial(api, caixa, cliente, loja, produto):
    resposta = api(caixa).post(
        "/api/pedidos/",
        {"cliente": cliente.pk, "loja": loja.pk, "itens": [{"produto": produto.pk, "quantidade": 1}]},
        format="json",
    )
    assert resposta.status_code == 409


def test_funcionario_precisa_informar_cliente_e_usar_sua_filial(api, caixa, cliente, outra_loja, loja, produto):
    itens = [{"produto": produto.pk, "quantidade": 1}]
    sem_cliente = api(caixa).post("/api/pedidos/", {"loja": loja.pk, "itens": itens}, format="json")
    assert sem_cliente.status_code == 400
    outra = api(caixa).post(
        "/api/pedidos/", {"cliente": cliente.pk, "loja": outra_loja.pk, "itens": itens}, format="json"
    )
    assert outra.status_code == 403


def test_usuario_cliente_sem_cadastro(api, criar_usuario, loja, produto):
    usuario = criar_usuario("CLIENTE", email="semcadastro@teste.com")
    resposta = api(usuario).post(
        "/api/pedidos/", {"loja": loja.pk, "itens": [{"produto": produto.pk, "quantidade": 1}]}, format="json"
    )
    assert resposta.status_code == 400


def test_fluxo_completo(api, pedido_criado, separador, caixa):
    url = f"/api/pedidos/{pedido_criado.pk}"
    separacao = api(separador).post(f"{url}/iniciar-separacao/")
    assert separacao.status_code == 201
    assert separacao.data["status"] == StatusSeparacao.EM_ANDAMENTO

    concluida = api(separador).post(f"/api/separacoes/{separacao.data['id']}/concluir/")
    assert concluida.status_code == 200
    assert concluida.data["status"] == StatusSeparacao.CONCLUIDA

    finalizado = api(caixa).post(f"{url}/finalizar/")
    assert finalizado.status_code == 200
    assert finalizado.data["status"] == StatusPedido.FINALIZADO

    assert api(caixa).post(f"{url}/cancelar/").status_code == 409


def test_transicao_invalida(api, pedido_criado, caixa):
    assert api(caixa).post(f"/api/pedidos/{pedido_criado.pk}/finalizar/").status_code == 409


def test_somente_separador_responsavel_conclui(api, pedido_criado, separador, criar_usuario, gerente):
    separacao = api(separador).post(f"/api/pedidos/{pedido_criado.pk}/iniciar-separacao/").data
    outro = criar_usuario("SEPARADOR", email="outro.separador@teste.com")
    url = f"/api/separacoes/{separacao['id']}/concluir/"
    assert api(outro).post(url).status_code == 403
    assert api(gerente).post(url).status_code == 200
    assert api(gerente).post(url).status_code == 409


def test_cancelar_devolve_estoque_e_encerra_separacao(api, pedido_criado, separador, caixa, estoque):
    api(separador).post(f"/api/pedidos/{pedido_criado.pk}/iniciar-separacao/")
    resposta = api(caixa).post(f"/api/pedidos/{pedido_criado.pk}/cancelar/")
    assert resposta.status_code == 200
    assert resposta.data["status"] == StatusPedido.CANCELADO
    assert resposta.data["separacoes"][0]["status"] == StatusSeparacao.CANCELADA
    estoque.refresh_from_db()
    assert estoque.quantidade == 10


def test_cliente_cancela_somente_pendente(api, pedido_criado, usuario_cliente, separador):
    api(separador).post(f"/api/pedidos/{pedido_criado.pk}/iniciar-separacao/")
    assert api(usuario_cliente).post(f"/api/pedidos/{pedido_criado.pk}/cancelar/").status_code == 403


def test_cliente_cancela_pendente(api, pedido_criado, usuario_cliente):
    assert api(usuario_cliente).post(f"/api/pedidos/{pedido_criado.pk}/cancelar/").status_code == 200


def test_escopo_de_pedidos(api, pedido_criado, usuario_cliente, criar_usuario, outra_loja, admin, separador):
    outro_usuario = criar_usuario("CLIENTE", email="outro.cliente@teste.com")
    Cliente.objects.create(usuario=outro_usuario, nome="Outro", email=outro_usuario.email)
    caixa_outra_loja = criar_usuario("CAIXA", loja_usuario=outra_loja, email="caixa.outra@teste.com")
    assert api(usuario_cliente).get("/api/pedidos/").data["count"] == 1
    assert api(outro_usuario).get("/api/pedidos/").data["count"] == 0
    assert api(caixa_outra_loja).get("/api/pedidos/").data["count"] == 0
    assert api(admin).get("/api/pedidos/").data["count"] == 1
    api(separador).post(f"/api/pedidos/{pedido_criado.pk}/iniciar-separacao/")
    assert api(separador).get("/api/separacoes/").data["count"] == 1


def test_cliente_nao_separa(api, pedido_criado, usuario_cliente):
    assert api(usuario_cliente).post(f"/api/pedidos/{pedido_criado.pk}/iniciar-separacao/").status_code == 403

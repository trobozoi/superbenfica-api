"""Testes da forma de entrega do pedido (retirada na loja ou entrega em domicílio)."""

import pytest
from django.db import IntegrityError

from apps.clientes.models import Cliente, EnderecoCliente
from apps.pedidos.models import Pedido, StatusPedido, TipoEntrega

pytestmark = pytest.mark.django_db


@pytest.fixture
def endereco(cliente: Cliente) -> EnderecoCliente:
    return EnderecoCliente.objects.create(
        cliente=cliente,
        endereco="Rua São José",
        numero="100",
        complemento="Apto 2",
        bairro="Centro",
        cidade="Fortaleza",
        estado="CE",
        cep="60060-170",
        principal=True,
    )


@pytest.fixture
def pedir(api, usuario_cliente, loja, estoque, produto, forma_pagamento):
    """Envia um pedido de 1x produto do cliente com os campos de entrega informados."""

    def _pedir(**entrega):
        corpo = {
            "loja": loja.pk,
            "forma_pagamento": forma_pagamento.pk,
            "itens": [{"produto": produto.pk, "quantidade": 1}],
            **entrega,
        }
        return api(usuario_cliente).post("/api/pedidos/", corpo, format="json")

    return _pedir


def test_sem_tipo_de_entrega_o_pedido_e_retirada_na_loja(pedir):
    resposta = pedir()
    assert resposta.status_code == 201, resposta.data
    assert resposta.data["tipo_entrega"] == TipoEntrega.RETIRADA
    assert resposta.data["endereco_entrega"] == ""


def test_entrega_em_domicilio_copia_o_endereco_para_o_pedido(pedir, endereco):
    resposta = pedir(tipo_entrega="DOMICILIO", endereco=endereco.pk)
    assert resposta.status_code == 201, resposta.data
    esperado = "Rua São José, 100 (Apto 2) - Centro, Fortaleza/CE - CEP 60060-170"
    assert resposta.data["tipo_entrega"] == TipoEntrega.DOMICILIO
    assert resposta.data["endereco_entrega"] == esperado

    # Mudar o endereço do cliente depois não altera o pedido já feito.
    endereco.numero = "999"
    endereco.save()
    assert Pedido.objects.get(pk=resposta.data["id"]).endereco_entrega == esperado


def test_domicilio_sem_endereco_retorna_400_e_nao_baixa_estoque(pedir, estoque):
    resposta = pedir(tipo_entrega="DOMICILIO")
    assert resposta.status_code == 400
    assert "endereco" in resposta.data
    estoque.refresh_from_db()
    assert estoque.quantidade == 10


def test_domicilio_com_endereco_de_outro_cliente_retorna_400(pedir, criar_usuario):
    outro_usuario = criar_usuario("CLIENTE", email="outro.cliente@example.com")
    outro = Cliente.objects.create(usuario=outro_usuario, nome="Outro", email=outro_usuario.email)
    alheio = EnderecoCliente.objects.create(
        cliente=outro,
        endereco="Rua A",
        numero="1",
        bairro="B",
        cidade="Fortaleza",
        estado="CE",
        cep="60000-000",
    )
    resposta = pedir(tipo_entrega="DOMICILIO", endereco=alheio.pk)
    assert resposta.status_code == 400
    assert "endereco" in resposta.data
    assert Pedido.objects.count() == 0


def test_retirada_ignora_endereco_informado(pedir, endereco):
    resposta = pedir(tipo_entrega="RETIRADA", endereco=endereco.pk)
    assert resposta.status_code == 201, resposta.data
    assert resposta.data["endereco_entrega"] == ""


def test_tipo_de_entrega_invalido_retorna_400(pedir):
    assert pedir(tipo_entrega="DRONE").status_code == 400


def test_funcionario_registra_entrega_com_endereco_do_cliente(
    api, caixa, cliente, loja, estoque, produto, forma_pagamento, endereco
):
    resposta = api(caixa).post(
        "/api/pedidos/",
        {
            "cliente": cliente.pk,
            "loja": loja.pk,
            "forma_pagamento": forma_pagamento.pk,
            "itens": [{"produto": produto.pk, "quantidade": 1}],
            "tipo_entrega": "DOMICILIO",
            "endereco": endereco.pk,
        },
        format="json",
    )
    assert resposta.status_code == 201, resposta.data
    assert resposta.data["endereco_entrega"].startswith("Rua São José, 100")


def test_filtra_pedidos_por_tipo_de_entrega(api, gerente, pedir, endereco):
    pedir()
    pedir(tipo_entrega="DOMICILIO", endereco=endereco.pk)
    resposta = api(gerente).get("/api/pedidos/", {"tipo_entrega": "DOMICILIO"})
    assert resposta.status_code == 200
    assert resposta.data["count"] == 1
    assert resposta.data["results"][0]["tipo_entrega"] == TipoEntrega.DOMICILIO


def test_banco_recusa_domicilio_sem_endereco(cliente, loja):
    with pytest.raises(IntegrityError):
        Pedido.objects.create(cliente=cliente, loja=loja, tipo_entrega=TipoEntrega.DOMICILIO)


@pytest.fixture
def separar(api, separador):
    """Leva o pedido até SEPARADO."""

    def _separar(pedido_id: int) -> None:
        separacao = api(separador).post(f"/api/pedidos/{pedido_id}/iniciar-separacao/")
        assert api(separador).post(f"/api/separacoes/{separacao.data['id']}/concluir/").status_code == 200

    return _separar


def test_entrega_em_domicilio_sai_para_entrega_antes_de_finalizar(api, caixa, pedir, endereco, separar):
    pedido_id = pedir(tipo_entrega="DOMICILIO", endereco=endereco.pk).data["id"]
    url = f"/api/pedidos/{pedido_id}"
    assert api(caixa).post(f"{url}/despachar/").status_code == 409
    separar(pedido_id)

    # Separado, o pedido de entrega não é finalizado direto no caixa.
    assert api(caixa).post(f"{url}/finalizar/").status_code == 409

    despachado = api(caixa).post(f"{url}/despachar/")
    assert despachado.status_code == 200
    assert despachado.data["status"] == StatusPedido.SAIU_PARA_ENTREGA

    finalizado = api(caixa).post(f"{url}/finalizar/")
    assert finalizado.status_code == 200
    assert finalizado.data["status"] == StatusPedido.FINALIZADO


def test_retirada_na_loja_nao_sai_para_entrega(api, caixa, pedir, separar):
    pedido_id = pedir().data["id"]
    separar(pedido_id)
    assert api(caixa).post(f"/api/pedidos/{pedido_id}/despachar/").status_code == 409
    assert api(caixa).post(f"/api/pedidos/{pedido_id}/finalizar/").status_code == 200


def test_pedido_que_saiu_para_entrega_pode_ser_cancelado(api, caixa, pedir, endereco, separar, estoque):
    pedido_id = pedir(tipo_entrega="DOMICILIO", endereco=endereco.pk).data["id"]
    separar(pedido_id)
    api(caixa).post(f"/api/pedidos/{pedido_id}/despachar/")
    cancelado = api(caixa).post(f"/api/pedidos/{pedido_id}/cancelar/")
    assert cancelado.status_code == 200
    assert cancelado.data["status"] == StatusPedido.CANCELADO
    estoque.refresh_from_db()
    assert estoque.quantidade == 10


def test_separador_nao_despacha(api, separador, pedir, endereco, separar):
    pedido_id = pedir(tipo_entrega="DOMICILIO", endereco=endereco.pk).data["id"]
    separar(pedido_id)
    assert api(separador).post(f"/api/pedidos/{pedido_id}/despachar/").status_code == 403

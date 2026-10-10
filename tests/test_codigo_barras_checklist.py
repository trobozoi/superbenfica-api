"""Testes do código de barras do produto e do checklist de itens da separação."""

import pytest

from apps.pedidos.models import ItemPedido
from apps.produtos.validators import gtin_valido

pytestmark = pytest.mark.django_db

EAN13 = "7891000315507"
EAN8 = "96385074"
UPC_A = "036000291452"
GTIN14 = "17891000315504"


@pytest.mark.parametrize("codigo", [EAN13, EAN8, UPC_A, GTIN14])
def test_gtin_valido(codigo):
    assert gtin_valido(codigo)


@pytest.mark.parametrize(
    "codigo",
    ["7891000315508", "789100031550", "12345", "78910003155O7", chr(0xFF17) * 13, ""],
)
def test_gtin_invalido(codigo):
    assert not gtin_valido(codigo)


def test_gerente_cadastra_produto_com_codigo_de_barras(api, gerente):
    dados = {"nome": "Leite 1L", "sku": "LTE-1", "preco": "5.49", "codigo_barras": EAN13}
    resposta = api(gerente).post("/api/produtos/", dados, format="json")
    assert resposta.status_code == 201, resposta.data
    assert resposta.data["codigo_barras"] == EAN13

    busca = api(gerente).get("/api/produtos/", {"codigo_barras": EAN13})
    assert [item["sku"] for item in busca.data["results"]] == ["LTE-1"]
    assert api(gerente).get("/api/produtos/", {"search": EAN13}).data["count"] == 1


def test_codigo_de_barras_invalido_ou_repetido(api, gerente, produto, produto_2):
    url = f"/api/produtos/{produto.pk}/"
    invalido = api(gerente).patch(url, {"codigo_barras": "7891000315508"}, format="json")
    assert invalido.status_code == 400
    assert "codigo_barras" in invalido.data

    assert api(gerente).patch(url, {"codigo_barras": EAN13}, format="json").status_code == 200
    # Salvar o mesmo produto de novo com o próprio código continua valendo.
    assert api(gerente).patch(url, {"codigo_barras": EAN13}, format="json").status_code == 200

    repetido = api(gerente).patch(f"/api/produtos/{produto_2.pk}/", {"codigo_barras": EAN13}, format="json")
    assert repetido.status_code == 400
    assert "codigo_barras" in repetido.data


def test_varios_produtos_sem_codigo_de_barras(api, gerente, produto, produto_2):
    for item in (produto, produto_2):
        resposta = api(gerente).patch(f"/api/produtos/{item.pk}/", {"codigo_barras": ""}, format="json")
        assert resposta.status_code == 200


@pytest.fixture
def pedido(api, usuario_cliente, loja, estoque, estoque_2, produto, produto_2, forma_pagamento):
    """Pedido com dois itens (produto com código de barras)."""
    produto.codigo_barras = EAN13
    produto.save(update_fields=["codigo_barras"])
    itens = [{"produto": produto.pk, "quantidade": 2}, {"produto": produto_2.pk, "quantidade": 1}]
    dados = {"loja": loja.pk, "forma_pagamento": forma_pagamento.pk, "itens": itens}
    resposta = api(usuario_cliente).post("/api/pedidos/", dados, format="json")
    assert resposta.status_code == 201, resposta.data
    return resposta.data


def iniciar(api, separador, pedido) -> int:
    resposta = api(separador).post(f"/api/pedidos/{pedido['id']}/iniciar-separacao/")
    assert resposta.status_code == 201
    return resposta.data["id"]


def test_itens_trazem_codigo_de_barras_e_checklist(pedido):
    item = next(item for item in pedido["itens"] if item["produto_sku"] == "ARZ-5")
    assert item["produto_codigo_barras"] == EAN13
    assert item["separado"] is False


def test_separador_marca_e_desmarca_itens(api, separador, pedido, monkeypatch):
    eventos = []
    monkeypatch.setattr("apps.pedidos.services.notificar_loja", lambda *args: eventos.append(args))
    separacao_id = iniciar(api, separador, pedido)
    eventos.clear()
    item_id = pedido["itens"][0]["id"]
    url = f"/api/separacoes/{separacao_id}/marcar-item/"

    marcado = api(separador).post(url, {"item": item_id, "separado": True}, format="json")
    assert marcado.status_code == 200, marcado.data
    assert marcado.data["separado"] is True
    assert ItemPedido.objects.get(pk=item_id).separado
    assert eventos[0][1] == "pedido.atualizado"

    # Repetir a mesma marcação não gera evento novo.
    api(separador).post(url, {"item": item_id, "separado": True}, format="json")
    assert len(eventos) == 1

    desmarcado = api(separador).post(url, {"item": item_id, "separado": False}, format="json")
    assert desmarcado.data["separado"] is False

    detalhe = api(separador).get(f"/api/pedidos/{pedido['id']}/")
    assert [item["separado"] for item in detalhe.data["itens"]] == [False, False]


def test_marcar_item_regras(api, separador, gerente, criar_usuario, pedido, produto):
    separacao_id = iniciar(api, separador, pedido)
    url = f"/api/separacoes/{separacao_id}/marcar-item/"
    item_id = pedido["itens"][0]["id"]

    outro = criar_usuario("SEPARADOR", email="outro.separador@teste.com")
    assert api(outro).post(url, {"item": item_id, "separado": True}, format="json").status_code == 403
    assert api(gerente).post(url, {"item": item_id, "separado": True}, format="json").status_code == 200

    de_outro_pedido = api(separador).post(url, {"item": 999_999, "separado": True}, format="json")
    assert de_outro_pedido.status_code == 400
    assert "item" in de_outro_pedido.data
    assert api(separador).post(url, {"separado": True}, format="json").status_code == 400

    assert api(separador).post(f"/api/separacoes/{separacao_id}/concluir/").status_code == 200
    concluida = api(separador).post(url, {"item": item_id, "separado": False}, format="json")
    assert concluida.status_code == 409

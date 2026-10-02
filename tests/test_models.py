"""Testes das regras dos models."""

from datetime import time
from decimal import Decimal

import pytest
from django.db import IntegrityError

from apps.clientes.models import EnderecoCliente
from apps.core.constants import Role
from apps.estoque.models import EstoqueLocal
from apps.filiais.models import Loja
from apps.pedidos.models import ItemPedido, Pedido, StatusPedido
from apps.produtos.models import Produto
from apps.usuarios.models import Usuario

pytestmark = pytest.mark.django_db


def test_loja_horario_comum(loja):
    assert str(loja) == "Loja Teste"
    assert loja.esta_aberta(time(12))
    assert not loja.esta_aberta(time(23))


def test_loja_que_fecha_depois_da_meia_noite():
    loja = Loja(nome="24h", endereco="x", horario_abertura=time(18), horario_fechamento=time(2))
    assert loja.esta_aberta(time(1))
    assert loja.esta_aberta(time(20))
    assert not loja.esta_aberta(time(10))


def test_usuario_manager():
    with pytest.raises(ValueError, match="e-mail"):
        Usuario.objects.create_user(email="", password="x")
    with pytest.raises(ValueError, match="Superusuário"):
        Usuario.objects.create_superuser(email="a@a.com", password="x", is_staff=False)
    root = Usuario.objects.create_superuser(email="ROOT@Teste.com", password="x", nome="Root")
    assert root.email == "root@teste.com"
    assert root.is_admin
    assert root.is_equipe
    assert root.role == Role.ADMIN
    assert str(root) == "Root <root@teste.com>"


def test_produto_preco_positivo():
    preco_zero = Decimal("0")
    with pytest.raises(IntegrityError):
        Produto.objects.create(nome="Grátis", sku="X-0", preco=preco_zero)


def test_estoque_unico_e_abaixo_do_minimo(estoque, produto, loja):
    assert not estoque.abaixo_do_minimo
    estoque.quantidade = 3
    assert estoque.abaixo_do_minimo
    assert "Arroz 5kg" in str(estoque)
    with pytest.raises(IntegrityError):
        EstoqueLocal.objects.create(produto=produto, loja=loja)


def test_endereco_principal_unico(cliente):
    dados = {"endereco": "Rua", "numero": "1", "bairro": "B", "cidade": "C", "estado": "CE", "cep": "60000-000"}
    endereco = EnderecoCliente.objects.create(cliente=cliente, principal=True, **dados)
    assert "Rua, 1" in str(endereco)
    with pytest.raises(IntegrityError):
        EnderecoCliente.objects.create(cliente=cliente, principal=True, **dados)


def test_pedido_total_e_transicoes(cliente, loja, produto, produto_2):
    pedido = Pedido.objects.create(cliente=cliente, loja=loja)
    ItemPedido.objects.create(pedido=pedido, produto=produto, quantidade=2, preco_unitario=Decimal("25.00"))
    item = ItemPedido.objects.create(pedido=pedido, produto=produto_2, quantidade=1, preco_unitario=Decimal("8.50"))
    assert pedido.total == Decimal("58.50")
    assert pedido.codigo.startswith("PED-")
    assert "Pendente" in str(pedido)
    assert str(item) == "1x Feijão 1kg"
    assert pedido.pode_mudar_para(StatusPedido.EM_SEPARACAO)
    assert not pedido.pode_mudar_para(StatusPedido.FINALIZADO)

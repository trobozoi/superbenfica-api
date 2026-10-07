"""Fixtures compartilhadas pelos testes.

Os testes rodam com ``config.settings.test`` (SQLite em memória), nunca no
banco do Supabase.
"""

from collections.abc import Callable
from datetime import time
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.clientes.models import Cliente
from apps.core.constants import Role
from apps.estoque.models import EstoqueLocal
from apps.filiais.models import Loja
from apps.pagamentos.models import FormaPagamento, TipoPagamento
from apps.produtos.models import Produto
from apps.usuarios.models import Usuario

SENHA_TESTE = "Senha-de-teste-123"


@pytest.fixture
def loja() -> Loja:
    """Filial principal dos testes."""
    return Loja.objects.create(
        nome="Loja Teste", endereco="Rua A, 1", horario_abertura=time(7), horario_fechamento=time(22)
    )


@pytest.fixture
def outra_loja() -> Loja:
    """Segunda filial, para testar o isolamento entre filiais."""
    return Loja.objects.create(
        nome="Outra Loja", endereco="Rua B, 2", horario_abertura=time(8), horario_fechamento=time(20)
    )


@pytest.fixture
def criar_usuario(loja: Loja) -> Callable[..., Usuario]:
    """Fábrica de usuários: ``criar_usuario(Role.CAIXA, loja=...)``."""

    def _criar(role: str, loja_usuario: Loja | None = None, email: str | None = None) -> Usuario:
        return Usuario.objects.create_user(
            email=email or f"{role.lower()}@teste.com",
            password=SENHA_TESTE,
            nome=f"Usuário {role}",
            role=role,
            loja=loja_usuario or loja,
        )

    return _criar


@pytest.fixture
def admin(criar_usuario: Callable[..., Usuario]) -> Usuario:
    """Usuário ADMIN."""
    return criar_usuario(Role.ADMIN)


@pytest.fixture
def gerente(criar_usuario: Callable[..., Usuario]) -> Usuario:
    """Usuário GERENTE da filial principal."""
    return criar_usuario(Role.GERENTE)


@pytest.fixture
def separador(criar_usuario: Callable[..., Usuario]) -> Usuario:
    """Usuário SEPARADOR da filial principal."""
    return criar_usuario(Role.SEPARADOR)


@pytest.fixture
def caixa(criar_usuario: Callable[..., Usuario]) -> Usuario:
    """Usuário CAIXA da filial principal."""
    return criar_usuario(Role.CAIXA)


@pytest.fixture
def usuario_cliente(criar_usuario: Callable[..., Usuario]) -> Usuario:
    """Usuário CLIENTE com cadastro de cliente vinculado."""
    usuario = criar_usuario(Role.CLIENTE)
    Cliente.objects.create(usuario=usuario, nome=usuario.nome, email=usuario.email, loja=usuario.loja)
    return usuario


@pytest.fixture
def cliente(usuario_cliente: Usuario) -> Cliente:
    """Cadastro de cliente do ``usuario_cliente``."""
    return usuario_cliente.cliente


@pytest.fixture
def produto() -> Produto:
    """Produto ativo."""
    return Produto.objects.create(nome="Arroz 5kg", sku="ARZ-5", preco=Decimal("25.00"))


@pytest.fixture
def produto_2() -> Produto:
    """Segundo produto ativo."""
    return Produto.objects.create(nome="Feijão 1kg", sku="FEJ-1", preco=Decimal("8.50"))


@pytest.fixture
def estoque(produto: Produto, loja: Loja) -> EstoqueLocal:
    """Estoque do ``produto`` na filial principal (10 unidades, mínimo 3)."""
    return EstoqueLocal.objects.create(produto=produto, loja=loja, quantidade=10, quantidade_minima=3)


@pytest.fixture
def estoque_2(produto_2: Produto, loja: Loja) -> EstoqueLocal:
    """Estoque do ``produto_2`` na filial principal (5 unidades)."""
    return EstoqueLocal.objects.create(produto=produto_2, loja=loja, quantidade=5, quantidade_minima=2)


@pytest.fixture
def forma_pagamento() -> FormaPagamento:
    """Forma "Pix" cadastrada pela migration pagamentos.0002."""
    return FormaPagamento.objects.get(tipo=TipoPagamento.PIX)


@pytest.fixture
def api() -> Callable[[Usuario | None], APIClient]:
    """Fábrica de clientes HTTP autenticados: ``api(usuario)``."""

    def _cliente(usuario: Usuario | None = None) -> APIClient:
        client = APIClient()
        if usuario is not None:
            client.force_authenticate(usuario)
        return client

    return _cliente

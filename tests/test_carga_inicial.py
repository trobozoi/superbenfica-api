"""Testes do comando ``carga_inicial``."""

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.clientes.models import Cliente
from apps.estoque.models import EstoqueLocal
from apps.filiais.models import Loja
from apps.pedidos.models import Pedido, Separacao
from apps.produtos.models import Produto
from apps.usuarios.models import Usuario

pytestmark = pytest.mark.django_db


@pytest.fixture
def variaveis_seed(monkeypatch):
    """Define as variáveis de ambiente exigidas pela carga inicial."""
    monkeypatch.setenv("DJANGO_SUPERUSER_EMAIL", "root@teste.com")
    monkeypatch.setenv("DJANGO_SUPERUSER_PASSWORD", "Senha-root-de-teste-1")
    monkeypatch.setenv("SEED_DEFAULT_PASSWORD", "Senha-seed-de-teste-1")


def contagens() -> dict[str, int]:
    """Quantidade de registros de cada entidade."""
    modelos = (Loja, Usuario, Produto, EstoqueLocal, Cliente, Pedido, Separacao)
    return {modelo.__name__: modelo.objects.count() for modelo in modelos}


def test_carga_inicial_e_idempotente(variaveis_seed):
    call_command("carga_inicial", verbosity=0)
    primeira = contagens()
    assert primeira == {
        "Loja": 3,
        "Usuario": 6,
        "Produto": 30,
        "EstoqueLocal": 90,
        "Cliente": 11,
        "Pedido": 5,
        "Separacao": 2,
    }
    call_command("carga_inicial", verbosity=2)
    assert contagens() == primeira
    assert EstoqueLocal.objects.filter(quantidade__lte=10).exists()
    assert Usuario.objects.get(email="root@teste.com").is_superuser


def test_exige_senha_no_ambiente(monkeypatch):
    monkeypatch.delenv("SEED_DEFAULT_PASSWORD", raising=False)
    with pytest.raises(CommandError, match="SEED_DEFAULT_PASSWORD"):
        call_command("carga_inicial", verbosity=0)


def test_reset_bloqueado_sem_debug(variaveis_seed):
    with pytest.raises(CommandError, match="DEBUG"):
        call_command("carga_inicial", reset=True, no_input=True, verbosity=0)


def test_reset_recria_dados(variaveis_seed, settings):
    settings.DEBUG = True
    call_command("carga_inicial", verbosity=0)
    Produto.objects.filter(sku="HRT-0001").update(nome="Alterado")
    call_command("carga_inicial", reset=True, no_input=True, verbosity=0)
    assert Produto.objects.get(sku="HRT-0001").nome == "Banana prata (kg)"
    assert contagens()["Pedido"] == 5


def test_reset_pede_confirmacao(variaveis_seed, settings, monkeypatch):
    settings.DEBUG = True
    monkeypatch.setattr("builtins.input", lambda _mensagem: "não")
    with pytest.raises(CommandError, match="cancelada"):
        call_command("carga_inicial", reset=True, verbosity=0)

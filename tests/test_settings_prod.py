"""Testes das travas de segurança do ``config.settings.prod``.

Cada cenário roda em um processo separado, pois o módulo de settings só é
avaliado uma vez por processo.
"""

import os
import subprocess
import sys

import pytest

AMBIENTE_PROD = {
    "DJANGO_SETTINGS_MODULE": "config.settings.prod",
    "DJANGO_SECRET_KEY": "chave-apenas-para-teste",
    "DJANGO_ALLOWED_HOSTS": "api.exemplo.com",
    "REDIS_URL": "redis://localhost:6379/0",
    "DB_HOST": "localhost",
    "DB_PORT": "5432",
    "DB_NAME": "teste",
    "DB_USER": "teste",
    "DB_PASSWORD": "teste",
}


def carregar_settings_prod(**sobrescritas: str) -> subprocess.CompletedProcess:
    """Importa o settings de produção em um subprocesso e retorna o resultado."""
    ambiente = {**os.environ, **AMBIENTE_PROD, **sobrescritas}
    return subprocess.run(
        [sys.executable, "-c", "import django; django.setup()"],
        env=ambiente,
        capture_output=True,
        text=True,
        check=False,
    )


def test_prod_carrega_com_todas_as_variaveis():
    assert carregar_settings_prod().returncode == 0


@pytest.mark.parametrize(
    ("variavel", "mensagem"),
    [
        ("REDIS_URL", "REDIS_URL"),
        ("DJANGO_SECRET_KEY", "DJANGO_SECRET_KEY"),
        ("DJANGO_ALLOWED_HOSTS", "DJANGO_ALLOWED_HOSTS"),
    ],
)
def test_prod_recusa_variavel_obrigatoria_vazia(variavel, mensagem):
    resultado = carregar_settings_prod(**{variavel: ""})
    assert resultado.returncode != 0
    assert "ImproperlyConfigured" in resultado.stderr
    assert mensagem in resultado.stderr

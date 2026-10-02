"""Testes das páginas HTML: apresentação (/) e Swagger personalizado."""

import pytest
from django.contrib.staticfiles import finders

from apps.core.views import MODULOS

pytestmark = pytest.mark.django_db


def test_pagina_inicial(client):
    resposta = client.get("/")
    assert resposta.status_code == 200
    html = resposta.content.decode()
    assert "Super Benfica" in html
    assert 'href="/api/docs/"' in html
    assert "core/css/inicio.css" in html
    for modulo in MODULOS:
        assert modulo.nome in html


def test_cartoes_apontam_para_secoes_do_swagger(client):
    html = client.get("/").content.decode()
    assert 'href="/api/docs/#/Produtos"' in html
    assert 'href="/api/docs/#/Relat%C3%B3rios"' in html


def test_swagger_usa_tema_e_assets_locais(client):
    html = client.get("/api/docs/").content.decode()
    assert "core/css/swagger.css" in html
    assert 'aria-current="page">Swagger' in html
    assert "drf_spectacular_sidecar/swagger-ui-dist/swagger-ui-bundle.js" in html
    assert "cdn.jsdelivr.net" not in html


def test_redoc_usa_assets_locais(client):
    html = client.get("/api/redoc/").content.decode()
    assert "drf_spectacular_sidecar/redoc" in html


@pytest.mark.parametrize(
    "arquivo", ["core/css/tema.css", "core/css/inicio.css", "core/css/swagger.css", "core/img/favicon.svg"]
)
def test_arquivos_estaticos_existem(arquivo):
    assert finders.find(arquivo) is not None

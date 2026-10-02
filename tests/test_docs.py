"""Testes da documentação OpenAPI / Swagger."""

import pytest
from django.core.management import call_command

pytestmark = pytest.mark.django_db


def test_schema_sem_avisos(tmp_path):
    """Gera o schema e falha se o drf-spectacular emitir qualquer aviso."""
    arquivo = tmp_path / "schema.yml"
    call_command("spectacular", "--validate", "--fail-on-warn", "--file", str(arquivo))
    conteudo = arquivo.read_text(encoding="utf-8")
    assert "Super Benfica API" in conteudo
    assert "/api/pedidos/{id}/iniciar-separacao/" in conteudo


def test_paginas_de_documentacao(client):
    assert client.get("/api/schema/").status_code == 200
    assert client.get("/api/docs/").status_code == 200
    assert client.get("/api/redoc/").status_code == 200

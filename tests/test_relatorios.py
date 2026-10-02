"""Testes dos relatórios gerenciais e da task de resumo diário."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.core.cache import cache
from django.utils import timezone

from apps.pedidos.models import ItemPedido, Pedido, StatusPedido
from apps.relatorios.tasks import gerar_resumo_diario

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def limpar_cache():
    """Isola o cache entre os testes."""
    cache.clear()


@pytest.fixture
def vendas(cliente, loja, produto, produto_2, estoque):
    """Dois pedidos finalizados e um pendente na filial principal."""
    for quantidade in (2, 1):
        pedido = Pedido.objects.create(cliente=cliente, loja=loja, status=StatusPedido.FINALIZADO)
        ItemPedido.objects.create(
            pedido=pedido, produto=produto, quantidade=quantidade, preco_unitario=Decimal("25.00")
        )
    pendente = Pedido.objects.create(cliente=cliente, loja=loja)
    ItemPedido.objects.create(pedido=pendente, produto=produto_2, quantidade=1, preco_unitario=Decimal("8.50"))


def test_vendas_por_loja(api, gerente, vendas):
    resposta = api(gerente).get("/api/relatorios/vendas/")
    assert resposta.status_code == 200
    linha = resposta.data[0]
    assert linha["pedidos"] == 2
    assert linha["faturamento"] == Decimal("75.00")
    assert linha["ticket_medio"] == Decimal("37.50")


def test_produtos_mais_vendidos(api, admin, vendas, produto):
    resposta = api(admin).get("/api/relatorios/produtos-mais-vendidos/", {"limite": 5})
    assert resposta.data[0]["sku"] == produto.sku
    assert resposta.data[0]["quantidade"] == 3


def test_pedidos_por_status(api, gerente, vendas):
    resposta = api(gerente).get("/api/relatorios/pedidos-por-status/")
    assert resposta.data[StatusPedido.FINALIZADO] == 2
    assert resposta.data[StatusPedido.PENDENTE] == 1


def test_estoque_baixo(api, admin, estoque, loja):
    estoque.quantidade = 1
    estoque.save()
    resposta = api(admin).get("/api/relatorios/estoque-baixo/", {"loja": loja.pk})
    assert resposta.data[0]["produto_nome"] == estoque.produto.nome


def test_filtro_por_periodo(api, gerente, vendas):
    amanha = (timezone.localdate() + timedelta(days=1)).isoformat()
    resposta = api(gerente).get("/api/relatorios/vendas/", {"inicio": amanha, "fim": amanha})
    assert resposta.data == []


def test_periodo_invalido(api, gerente):
    resposta = api(gerente).get("/api/relatorios/vendas/", {"inicio": "2026-02-01", "fim": "2026-01-01"})
    assert resposta.status_code == 400


def test_gerente_nao_consulta_outra_filial(api, gerente, outra_loja):
    assert api(gerente).get("/api/relatorios/vendas/", {"loja": outra_loja.pk}).status_code == 403


def test_caixa_nao_acessa_relatorios(api, caixa):
    assert api(caixa).get("/api/relatorios/vendas/").status_code == 403


def test_resumo_diario():
    resultado = gerar_resumo_diario.delay().get()
    ontem = (timezone.localdate() - timedelta(days=1)).isoformat()
    assert resultado == {"data": ontem, "filiais": 0}
    assert cache.get(f"relatorios:resumo:{ontem}")["data"] == ontem

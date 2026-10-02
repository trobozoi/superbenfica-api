"""Rotas dos relatórios (``/api/relatorios/``)."""

from django.urls import path

from apps.relatorios.views import (
    EstoqueBaixoView,
    PedidosPorStatusView,
    ProdutosMaisVendidosView,
    VendasPorLojaView,
)

urlpatterns = [
    path("vendas/", VendasPorLojaView.as_view(), name="relatorio-vendas"),
    path("produtos-mais-vendidos/", ProdutosMaisVendidosView.as_view(), name="relatorio-mais-vendidos"),
    path("pedidos-por-status/", PedidosPorStatusView.as_view(), name="relatorio-status"),
    path("estoque-baixo/", EstoqueBaixoView.as_view(), name="relatorio-estoque-baixo"),
]

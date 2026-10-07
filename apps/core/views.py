"""Páginas HTML do projeto: apresentação da API e Swagger com a identidade visual.

Nenhuma das páginas expõe dados de negócio; elas apenas descrevem a API e
apontam para a documentação.
"""

from dataclasses import dataclass
from typing import Any

from django.conf import settings
from django.views.generic import TemplateView
from drf_spectacular.utils import extend_schema
from drf_spectacular.views import SpectacularSwaggerView


@dataclass(frozen=True)
class Modulo:
    """Módulo da API exibido na página inicial."""

    nome: str
    rota: str
    descricao: str
    icone: str
    """Nome do ícone em ``core/_icone.html``."""


MODULOS = (
    Modulo("Autenticação", "/api/auth/", "Login JWT, renovação e revogação de tokens, autocadastro.", "cadeado"),
    Modulo("Filiais", "/api/lojas/", "Lojas da rede, horários de funcionamento e status.", "loja"),
    Modulo("Usuários", "/api/usuarios/", "Equipe por filial com perfis de acesso.", "usuarios"),
    Modulo("Produtos", "/api/produtos/", "Catálogo da rede com SKU, código de barras, preço e foto.", "carrinho"),
    Modulo("Estoque", "/api/estoques/", "Saldo independente por filial e ajustes com bloqueio.", "pacote"),
    Modulo("Clientes", "/api/clientes/", "Cadastro de clientes e endereços de entrega.", "endereco"),
    Modulo("Formas de pagamento", "/api/formas-pagamento/", "Pix, cartões, dinheiro e vale-alimentação.", "cartao"),
    Modulo(
        "Pedidos",
        "/api/pedidos/",
        "Do pedido à entrega: checklist de separação, finalização e cancelamento.",
        "caminhao",
    ),
    Modulo("Relatórios", "/api/relatorios/vendas/", "Vendas, ranking de produtos e estoque a repor.", "grafico"),
)

PERFIS = (
    ("ADMIN", "Acesso total, todas as filiais"),
    ("GERENTE", "Gestão e relatórios da filial"),
    ("SEPARADOR", "Separação de pedidos"),
    ("CAIXA", "Vendas e finalização"),
    ("CLIENTE", "Catálogo e próprios pedidos"),
)


def contexto_marca() -> dict[str, Any]:
    """Dados de identidade usados pelo cabeçalho de todas as páginas."""
    return {
        "versao": settings.SPECTACULAR_SETTINGS["VERSION"],
        "ambiente": "desenvolvimento" if settings.DEBUG else "produção",
    }


class PaginaInicialView(TemplateView):
    """Página de apresentação em ``/``."""

    template_name = "core/inicio.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """Adiciona módulos, perfis e dados da marca ao template."""
        contexto = super().get_context_data(**kwargs)
        contexto.update(contexto_marca(), modulos=MODULOS, perfis=PERFIS, pagina="inicio")
        return contexto


class SwaggerView(SpectacularSwaggerView):
    """Swagger UI com cabeçalho, guia rápido e tema do Super Benfica."""

    template_name = "core/swagger_ui.html"

    @extend_schema(exclude=True)
    def get(self, request: Any, *args: Any, **kwargs: Any) -> Any:
        """Acrescenta os dados da marca ao contexto do drf-spectacular."""
        resposta = super().get(request, *args, **kwargs)
        resposta.data.update(contexto_marca(), pagina="docs")
        return resposta

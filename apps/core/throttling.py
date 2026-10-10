"""Rate limit por endpoint.

Além dos limites globais (``anon`` e ``user``), endpoints sensíveis ou
custosos têm um escopo próprio, aplicado pelo ``ScopedRateThrottle`` do DRF.
Os limites de cada escopo ficam em ``REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]``.

Quando o limite estoura, a API responde **429 Too Many Requests** com o
cabeçalho ``Retry-After``. A contagem usa o cache do Django: em produção,
com Redis, ela é compartilhada por todos os processos.
"""

from rest_framework.throttling import BaseThrottle


class Escopo:
    """Nomes dos escopos de rate limit (um por grupo de endpoints)."""

    LOGIN = "login"
    JWT = "jwt"
    REGISTRO = "registro"
    PEDIDOS_CRIACAO = "pedidos_criacao"
    PEDIDOS_FLUXO = "pedidos_fluxo"
    ESTOQUE_AJUSTE = "estoque_ajuste"
    UPLOAD = "upload"
    RELATORIOS = "relatorios"


class ThrottlePorAcaoMixin:
    """Aplica um escopo de rate limit apenas a determinadas ações do ViewSet.

    Exemplo::

        throttle_scopes_por_acao = {"create": Escopo.PEDIDOS_CRIACAO}

    Ações sem entrada ficam só com os limites globais.
    """

    throttle_scopes_por_acao: dict[str, str] = {}

    def get_throttles(self) -> list[BaseThrottle]:
        """Define ``throttle_scope`` conforme a ação atual antes de instanciar os throttles."""
        self.throttle_scope = self.throttle_scopes_por_acao.get(getattr(self, "action", None) or "")
        return super().get_throttles()

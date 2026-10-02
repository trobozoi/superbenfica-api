"""Constantes de domínio compartilhadas entre os apps.

Centralizar roles e grupos de roles evita literais duplicados (regra S1192 do
SonarQube) e garante que permissões e models usem os mesmos valores.
"""

from django.db import models


class Role(models.TextChoices):
    """Perfis de acesso dos usuários do sistema."""

    ADMIN = "ADMIN", "Administrador"
    GERENTE = "GERENTE", "Gerente"
    SEPARADOR = "SEPARADOR", "Separador"
    CAIXA = "CAIXA", "Caixa"
    CLIENTE = "CLIENTE", "Cliente"


ROLES_GESTAO = (Role.ADMIN, Role.GERENTE)
"""Roles com poder de gestão (cadastros e relatórios)."""

ROLES_SEPARACAO = (Role.ADMIN, Role.GERENTE, Role.SEPARADOR)
"""Roles que podem separar pedidos."""

ROLES_VENDA = (Role.ADMIN, Role.GERENTE, Role.CAIXA)
"""Roles que podem criar e finalizar pedidos no balcão."""

ROLES_EQUIPE = (Role.ADMIN, Role.GERENTE, Role.SEPARADOR, Role.CAIXA)
"""Todos os funcionários (qualquer role exceto cliente)."""

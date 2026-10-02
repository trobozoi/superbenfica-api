"""Permissões DRF baseadas no role do usuário.

Cada classe libera o acesso apenas para usuários autenticados cujo role esteja
em ``allowed_roles``. Superusuários sempre têm acesso.
"""

from typing import Any

from rest_framework.permissions import BasePermission
from rest_framework.request import Request

from apps.core.constants import ROLES_EQUIPE, ROLES_GESTAO, ROLES_SEPARACAO, ROLES_VENDA, Role


def usuario_tem_role(user: Any, roles: tuple[str, ...]) -> bool:
    """Indica se ``user`` está autenticado e possui um dos ``roles``."""
    if not (user and user.is_authenticated):
        return False
    return bool(user.is_superuser or user.role in roles)


class HasRole(BasePermission):
    """Permissão base: subclasses definem ``allowed_roles``."""

    allowed_roles: tuple[str, ...] = ()
    message = "Seu perfil não tem permissão para esta operação."

    def has_permission(self, request: Request, view: Any) -> bool:
        """Verifica o role do usuário da requisição."""
        return usuario_tem_role(request.user, self.allowed_roles)


class IsAdmin(HasRole):
    """Somente administradores."""

    allowed_roles = (Role.ADMIN,)


class IsGestao(HasRole):
    """Administradores e gerentes."""

    allowed_roles = ROLES_GESTAO


class IsEquipe(HasRole):
    """Qualquer funcionário (não cliente)."""

    allowed_roles = ROLES_EQUIPE


class IsEquipeSeparacao(HasRole):
    """Administradores, gerentes e separadores."""

    allowed_roles = ROLES_SEPARACAO


class IsEquipeVenda(HasRole):
    """Administradores, gerentes e caixas."""

    allowed_roles = ROLES_VENDA


class IsCliente(HasRole):
    """Somente clientes."""

    allowed_roles = (Role.CLIENTE,)

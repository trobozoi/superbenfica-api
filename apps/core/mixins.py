"""Mixins de ViewSet reutilizados pelos apps.

- ``PermissoesPorAcaoMixin``: define permissões diferentes por ação do ViewSet.
- ``LojaScopedQuerysetMixin``: restringe o queryset à filial do usuário.
"""

from typing import Any

from django.db.models import QuerySet
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission

from apps.core.constants import Role


def usuario_e_admin(user: Any) -> bool:
    """Indica se o usuário tem acesso irrestrito a todas as filiais."""
    return bool(user.is_authenticated and (user.is_superuser or user.role == Role.ADMIN))


def validar_loja_do_usuario(user: Any, loja_id: int | None) -> None:
    """Impede que funcionários não-admin operem em outra filial.

    Raises:
        PermissionDenied: se a filial informada não é a do usuário.
    """
    if usuario_e_admin(user):
        return
    if loja_id is None or loja_id != user.loja_id:
        raise PermissionDenied("Você só pode operar na sua própria filial.")


class PermissoesPorAcaoMixin:
    """Permite declarar permissões por ação (``list``, ``create``, ações extras).

    Exemplo::

        permissoes_por_acao = {"create": (IsGestao,), "list": (IsAuthenticated,)}

    Ações sem entrada usam ``permission_classes`` do ViewSet.
    """

    permissoes_por_acao: dict[str, tuple[type[BasePermission], ...]] = {}

    def get_permissions(self) -> list[BasePermission]:
        """Instancia as permissões da ação atual."""
        classes = self.permissoes_por_acao.get(self.action, self.permission_classes)
        return [permissao() for permissao in classes]


class LojaScopedQuerysetMixin:
    """Filtra o queryset pela filial do usuário autenticado.

    Administradores veem todas as filiais. Demais usuários veem apenas os
    registros cujo campo ``loja_lookup`` aponta para a própria filial.
    """

    loja_lookup = "loja_id"

    def get_queryset(self) -> QuerySet:
        """Aplica o filtro de filial ao queryset base."""
        queryset = super().get_queryset()
        if getattr(self, "swagger_fake_view", False):
            return queryset.none()
        user = self.request.user
        if usuario_e_admin(user):
            return queryset
        if not user.is_authenticated or user.loja_id is None:
            return queryset.none()
        return queryset.filter(**{self.loja_lookup: user.loja_id})

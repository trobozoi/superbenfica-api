"""Models do app ``usuarios``.

O usuário do sistema autentica por e-mail e possui um ``role`` que define o
que pode fazer. Funcionários ficam vinculados a uma filial (``loja``).
"""

from typing import Any

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone

from apps.core.constants import ROLES_EQUIPE, Role


class UsuarioManager(BaseUserManager):
    """Manager com criação de usuários e superusuários por e-mail."""

    use_in_migrations = True

    def _criar(self, email: str, password: str | None, **campos: Any) -> "Usuario":
        """Cria o usuário com e-mail normalizado e senha criptografada."""
        if not email:
            raise ValueError("O e-mail é obrigatório.")
        usuario = self.model(email=self.normalize_email(email).lower(), **campos)
        usuario.set_password(password)
        usuario.save(using=self._db)
        return usuario

    def create_user(self, email: str, password: str | None = None, **campos: Any) -> "Usuario":
        """Cria um usuário comum."""
        campos.setdefault("is_staff", False)
        campos.setdefault("is_superuser", False)
        return self._criar(email, password, **campos)

    def create_superuser(self, email: str, password: str | None = None, **campos: Any) -> "Usuario":
        """Cria um superusuário com role ADMIN."""
        campos.setdefault("is_staff", True)
        campos.setdefault("is_superuser", True)
        campos.setdefault("role", Role.ADMIN)
        if not (campos["is_staff"] and campos["is_superuser"]):
            raise ValueError("Superusuário precisa de is_staff=True e is_superuser=True.")
        return self._criar(email, password, **campos)


class Usuario(AbstractBaseUser, PermissionsMixin):
    """Usuário do sistema (funcionário ou cliente)."""

    nome = models.CharField("nome", max_length=150)
    email = models.EmailField("e-mail", unique=True)
    telefone = models.CharField("telefone", max_length=20, blank=True, default="")
    loja = models.ForeignKey(
        "filiais.Loja",
        verbose_name="loja",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="usuarios",
    )
    role = models.CharField("perfil", max_length=20, choices=Role.choices, default=Role.CLIENTE)
    is_active = models.BooleanField("ativo", default=True)
    is_staff = models.BooleanField("acesso ao admin", default=False)
    data_cadastro = models.DateTimeField("data de cadastro", default=timezone.now)

    objects = UsuarioManager()

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = ["nome"]

    class Meta:
        db_table = "sb_usuario"
        ordering = ["nome"]
        verbose_name = "usuário"
        verbose_name_plural = "usuários"
        indexes = [models.Index(fields=["role"], name="sb_usuario_role_idx")]

    def __str__(self) -> str:
        return f"{self.nome} <{self.email}>"

    @property
    def is_admin(self) -> bool:
        """Administrador do sistema (acesso a todas as filiais)."""
        return self.is_superuser or self.role == Role.ADMIN

    @property
    def is_equipe(self) -> bool:
        """Funcionário de alguma filial (qualquer role exceto cliente)."""
        return self.is_superuser or self.role in ROLES_EQUIPE

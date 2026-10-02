"""Endpoints REST do app ``usuarios`` (gestão de usuários e autenticação)."""

from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import generics, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import BaseSerializer
from rest_framework_simplejwt.views import (
    TokenBlacklistView,
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

from apps.core.mixins import LojaScopedQuerysetMixin, PermissoesPorAcaoMixin
from apps.core.permissions import IsGestao
from apps.usuarios.models import Usuario
from apps.usuarios.serializers import (
    RegistroClienteSerializer,
    TokenComPerfilSerializer,
    UsuarioCreateSerializer,
    UsuarioSerializer,
)

TAG_USUARIOS = "Usuários"
TAG_AUTH = "Autenticação"


@extend_schema_view(
    list=extend_schema(
        tags=[TAG_USUARIOS],
        summary="Listar usuários",
        description="ADMIN vê todos; GERENTE vê apenas os usuários da própria filial.",
    ),
    retrieve=extend_schema(tags=[TAG_USUARIOS], summary="Detalhar usuário"),
    create=extend_schema(
        tags=[TAG_USUARIOS],
        summary="Cadastrar usuário",
        description="GERENTE só cadastra usuários da própria filial e não pode criar ADMIN.",
    ),
    update=extend_schema(tags=[TAG_USUARIOS], summary="Atualizar usuário"),
    partial_update=extend_schema(tags=[TAG_USUARIOS], summary="Atualizar parcialmente usuário"),
    destroy=extend_schema(
        tags=[TAG_USUARIOS],
        summary="Desativar usuário",
        description="O usuário é desativado (``is_active=false``), não removido.",
    ),
)
class UsuarioViewSet(PermissoesPorAcaoMixin, LojaScopedQuerysetMixin, viewsets.ModelViewSet):
    """Gestão de usuários (ADMIN e GERENTE) e consulta do próprio perfil."""

    queryset = Usuario.objects.select_related("loja")
    serializer_class = UsuarioSerializer
    permission_classes = (IsGestao,)
    permissoes_por_acao = {"me": (IsAuthenticated,)}
    filterset_fields = ("role", "loja", "is_active")
    search_fields = ("nome", "email")
    ordering_fields = ("nome", "data_cadastro")

    def get_serializer_class(self) -> type[BaseSerializer]:
        """Usa o serializer com senha apenas na criação."""
        if self.action == "create":
            return UsuarioCreateSerializer
        return UsuarioSerializer

    def perform_destroy(self, instance: Usuario) -> None:
        """Desativa o usuário em vez de excluí-lo."""
        instance.is_active = False
        instance.save(update_fields=["is_active"])

    @extend_schema(tags=[TAG_USUARIOS], summary="Meu perfil", responses=UsuarioSerializer)
    @action(detail=False, methods=["get"])
    def me(self, request: Request) -> Response:
        """Retorna os dados do usuário autenticado."""
        return Response(UsuarioSerializer(request.user, context={"request": request}).data)


@extend_schema(
    tags=[TAG_AUTH],
    summary="Obter tokens JWT",
    description="Recebe e-mail e senha e retorna os tokens ``access`` e ``refresh``.",
)
class LoginView(TokenObtainPairView):
    """Login: emite o par de tokens com as claims de perfil."""

    serializer_class = TokenComPerfilSerializer


@extend_schema(tags=[TAG_AUTH], summary="Renovar token de acesso")
class RenovarTokenView(TokenRefreshView):
    """Troca um ``refresh`` válido por um novo ``access`` (com rotação)."""


@extend_schema(tags=[TAG_AUTH], summary="Validar token")
class VerificarTokenView(TokenVerifyView):
    """Indica se um token ainda é válido."""


@extend_schema(
    tags=[TAG_AUTH],
    summary="Logout",
    description="Invalida o ``refresh`` informado (blacklist).",
)
class LogoutView(TokenBlacklistView):
    """Revoga o token de atualização."""


@extend_schema(
    tags=[TAG_AUTH],
    summary="Cadastro de cliente",
    description="Cadastro público: cria um usuário com role CLIENTE e o respectivo cliente.",
    responses={status.HTTP_201_CREATED: UsuarioSerializer},
)
class RegistroClienteView(mixins.CreateModelMixin, generics.GenericAPIView):
    """Autocadastro de clientes (não exige autenticação)."""

    serializer_class = RegistroClienteSerializer
    permission_classes = (AllowAny,)
    authentication_classes = ()

    def post(self, request: Request) -> Response:
        """Cria o cliente e retorna os dados do usuário."""
        return self.create(request)

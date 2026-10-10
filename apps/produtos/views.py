"""Endpoints REST do app ``produtos``."""

from django.db.models import QuerySet
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from apps.core.mixins import PermissoesPorAcaoMixin
from apps.core.permissions import IsGestao
from apps.core.throttling import Escopo, ThrottlePorAcaoMixin
from apps.produtos.fotos import FotoInvalidaError, remover_foto, salvar_foto
from apps.produtos.models import Produto
from apps.produtos.serializers import FotoProdutoSerializer, ProdutoSerializer

TAG = "Produtos"


@extend_schema_view(
    list=extend_schema(
        tags=[TAG],
        summary="Listar produtos",
        description=(
            "Clientes veem apenas produtos ativos. Filtros: ``categoria``, ``ativo``, ``codigo_barras``; "
            "busca por nome/SKU/código de barras."
        ),
    ),
    retrieve=extend_schema(tags=[TAG], summary="Detalhar produto"),
    create=extend_schema(tags=[TAG], summary="Cadastrar produto", description="ADMIN e GERENTE."),
    update=extend_schema(tags=[TAG], summary="Atualizar produto", description="ADMIN e GERENTE."),
    partial_update=extend_schema(tags=[TAG], summary="Atualizar parcialmente produto"),
    destroy=extend_schema(
        tags=[TAG],
        summary="Desativar produto",
        description="O produto é desativado (``ativo=false``) para preservar o histórico de pedidos.",
    ),
)
class ProdutoViewSet(ThrottlePorAcaoMixin, PermissoesPorAcaoMixin, viewsets.ModelViewSet):
    """Catálogo de produtos. Leitura para todos; escrita para a gestão."""

    queryset = Produto.objects.all()
    serializer_class = ProdutoSerializer
    permission_classes = (IsGestao,)
    permissoes_por_acao = {"list": (IsAuthenticated,), "retrieve": (IsAuthenticated,)}
    throttle_scopes_por_acao = {"foto": Escopo.UPLOAD}
    filterset_fields = ("categoria", "ativo", "codigo_barras")
    search_fields = ("nome", "sku", "codigo_barras", "descricao")
    ordering_fields = ("nome", "preco", "data_criacao")

    def get_queryset(self) -> QuerySet[Produto]:
        """Oculta produtos inativos de quem não é funcionário."""
        queryset = super().get_queryset()
        if getattr(self, "swagger_fake_view", False):
            return queryset
        if not self.request.user.is_equipe:
            return queryset.filter(ativo=True)
        return queryset

    def perform_destroy(self, instance: Produto) -> None:
        """Desativa o produto em vez de excluí-lo."""
        instance.ativo = False
        instance.save(update_fields=["ativo", "data_atualizacao"])

    @extend_schema(
        tags=[TAG],
        summary="Enviar foto do produto",
        description=(
            "ADMIN e GERENTE. Multipart com o campo ``foto`` (JPEG, PNG ou WebP, até 2 MB). "
            "A imagem é validada pelo conteúdo, regravada em WebP (máx. 1200 px, sem metadados) "
            "e substitui a foto anterior."
        ),
        request={"multipart/form-data": FotoProdutoSerializer},
        responses={200: ProdutoSerializer},
        methods=["POST"],
    )
    @extend_schema(
        tags=[TAG],
        summary="Remover foto do produto",
        description="ADMIN e GERENTE.",
        responses={204: None},
        methods=["DELETE"],
    )
    @action(detail=True, methods=["post", "delete"], parser_classes=[MultiPartParser])
    def foto(self, request: Request, pk: str | None = None) -> Response:
        """Envia (POST) ou remove (DELETE) a foto do produto."""
        produto = self.get_object()
        if request.method == "DELETE":
            remover_foto(produto)
            return Response(status=status.HTTP_204_NO_CONTENT)

        entrada = FotoProdutoSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        try:
            salvar_foto(produto, entrada.validated_data["foto"])
        except FotoInvalidaError as exc:
            return Response({"foto": [str(exc)]}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(produto).data)

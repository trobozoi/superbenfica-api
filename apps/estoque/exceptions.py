"""Exceções de negócio do estoque, convertidas pelo DRF em respostas HTTP."""

from rest_framework import status
from rest_framework.exceptions import APIException


class EstoqueInsuficienteError(APIException):
    """Saldo insuficiente para concluir a operação (HTTP 409)."""

    status_code = status.HTTP_409_CONFLICT
    default_detail = "Estoque insuficiente."
    default_code = "estoque_insuficiente"


class ProdutoIndisponivelError(APIException):
    """Produto inativo ou sem estoque cadastrado na filial (HTTP 409)."""

    status_code = status.HTTP_409_CONFLICT
    default_detail = "Produto indisponível nesta filial."
    default_code = "produto_indisponivel"

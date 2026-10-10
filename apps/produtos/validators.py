"""Validadores do app ``produtos``."""

from django.core.exceptions import ValidationError

TAMANHOS_GTIN = frozenset({8, 12, 13, 14})


def gtin_valido(valor: str) -> bool:
    """Indica se ``valor`` é um GTIN (EAN-8, UPC-A, EAN-13 ou GTIN-14) com dígito verificador correto."""
    if not (valor.isascii() and valor.isdigit()) or len(valor) not in TAMANHOS_GTIN:
        return False
    *corpo, verificador = (int(digito) for digito in valor)
    # Da direita para a esquerda (sem o verificador), os pesos alternam 3, 1, 3, 1...
    soma = sum(digito * (3 if indice % 2 == 0 else 1) for indice, digito in enumerate(reversed(corpo)))
    return (10 - soma % 10) % 10 == verificador


def validar_codigo_barras(valor: str) -> None:
    """Aceita vazio (produto sem código) ou um GTIN válido."""
    if valor and not gtin_valido(valor):
        raise ValidationError(
            "Código de barras inválido. Use EAN-8, EAN-13, UPC-A ou GTIN-14 (somente números).",
            code="codigo_barras_invalido",
        )

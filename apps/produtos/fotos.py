"""Tratamento das fotos de produto.

Toda imagem enviada é aberta pelo Pillow e **regravada** em WebP antes de ir para o disco:

- o tipo é decidido pelo conteúdo do arquivo, não pela extensão ou pelo Content-Type;
- metadados (EXIF, GPS) são descartados;
- arquivos "poliglotas" (imagem + script) não sobrevivem à regravação;
- o nome final é um UUID, sem nada vindo do usuário (evita path traversal).
"""

from io import BytesIO
from uuid import uuid4

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import UploadedFile
from PIL import Image, ImageOps, UnidentifiedImageError

from apps.produtos.models import Produto

FORMATOS_ACEITOS = frozenset({"JPEG", "PNG", "WEBP"})
# Limite de pixels para recusar "bombas de descompressão" antes de decodificar.
MAX_PIXELS = 40_000_000
QUALIDADE_WEBP = 85


class FotoInvalidaError(ValueError):
    """A imagem enviada não pode ser aceita (tipo, tamanho ou conteúdo)."""


def _abrir_imagem(arquivo: UploadedFile) -> Image.Image:
    if arquivo.size is None or arquivo.size > settings.FOTO_PRODUTO_MAX_BYTES:
        limite_mb = settings.FOTO_PRODUTO_MAX_BYTES // (1024 * 1024)
        raise FotoInvalidaError(f"A foto deve ter no máximo {limite_mb} MB.")
    try:
        imagem = Image.open(arquivo)
        if imagem.format not in FORMATOS_ACEITOS:
            raise FotoInvalidaError("Envie uma imagem JPEG, PNG ou WebP.")
        if imagem.width * imagem.height > MAX_PIXELS:
            raise FotoInvalidaError("A imagem tem resolução grande demais.")
        imagem.load()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise FotoInvalidaError("O arquivo enviado não é uma imagem válida.") from exc
    return imagem


def preparar_foto(arquivo: UploadedFile) -> ContentFile:
    """Valida, corrige a orientação, reduz e converte a imagem para WebP."""
    imagem = _abrir_imagem(arquivo)
    imagem = ImageOps.exif_transpose(imagem)
    imagem.thumbnail((settings.FOTO_PRODUTO_MAX_LADO, settings.FOTO_PRODUTO_MAX_LADO))
    if imagem.mode not in ("RGB", "RGBA"):
        imagem = imagem.convert("RGBA" if "A" in imagem.getbands() else "RGB")
    saida = BytesIO()
    imagem.save(saida, format="WEBP", quality=QUALIDADE_WEBP, method=4)
    return ContentFile(saida.getvalue(), name=f"{uuid4().hex}.webp")


def salvar_foto(produto: Produto, arquivo: UploadedFile) -> Produto:
    """Substitui a foto do produto, apagando o arquivo anterior do disco."""
    nova = preparar_foto(arquivo)
    anterior = produto.foto.name if produto.foto else ""
    produto.foto.save(nova.name, nova, save=False)
    produto.save(update_fields=["foto", "data_atualizacao"])
    if anterior:
        produto.foto.storage.delete(anterior)
    return produto


def remover_foto(produto: Produto) -> Produto:
    """Remove a foto do produto e o arquivo do disco."""
    if produto.foto:
        produto.foto.delete(save=False)
        produto.foto = ""
        produto.save(update_fields=["foto", "data_atualizacao"])
    return produto

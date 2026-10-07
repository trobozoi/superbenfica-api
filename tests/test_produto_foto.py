"""Testes do upload de foto de produto (POST/DELETE /api/produtos/{id}/foto/)."""

from io import BytesIO
from pathlib import Path

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from apps.produtos.fotos import MAX_PIXELS

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def media_temporaria(settings, tmp_path: Path) -> Path:
    """Cada teste grava as fotos numa pasta temporária, nunca em media/ do projeto."""
    settings.MEDIA_ROOT = tmp_path
    return tmp_path


def imagem(formato: str = "PNG", tamanho: tuple[int, int] = (64, 48), nome: str = "foto.png", exif: bool = False):
    """Gera um arquivo de imagem em memória para upload."""
    buffer = BytesIO()
    img = Image.new("RGB", tamanho, (200, 30, 30))
    extra = {}
    if exif:
        dados_exif = Image.Exif()
        dados_exif[0x010F] = "Fabricante de teste"  # Make
        extra["exif"] = dados_exif
    img.save(buffer, format=formato, **extra)
    return SimpleUploadedFile(nome, buffer.getvalue(), content_type=f"image/{formato.lower()}")


def url_foto(produto) -> str:
    return f"/api/produtos/{produto.pk}/foto/"


def test_gerente_envia_foto_convertida_para_webp(api, gerente, produto, media_temporaria):
    resposta = api(gerente).post(url_foto(produto), {"foto": imagem()}, format="multipart")
    assert resposta.status_code == 200, resposta.data
    assert resposta.data["foto"].startswith("http://testserver/media/produtos/")
    assert resposta.data["foto"].endswith(".webp")

    produto.refresh_from_db()
    arquivo = media_temporaria / produto.foto.name
    assert arquivo.exists()
    with Image.open(arquivo) as salva:
        assert salva.format == "WEBP"


def test_imagem_grande_e_reduzida_e_perde_metadados(api, gerente, produto, media_temporaria):
    foto = imagem("JPEG", tamanho=(2400, 1600), nome="grande.jpg", exif=True)
    assert api(gerente).post(url_foto(produto), {"foto": foto}, format="multipart").status_code == 200

    produto.refresh_from_db()
    with Image.open(media_temporaria / produto.foto.name) as salva:
        assert max(salva.size) == 1200
        assert not salva.getexif()


def test_nova_foto_substitui_e_apaga_a_anterior(api, gerente, produto, media_temporaria):
    cliente_http = api(gerente)
    cliente_http.post(url_foto(produto), {"foto": imagem()}, format="multipart")
    produto.refresh_from_db()
    anterior = media_temporaria / produto.foto.name

    cliente_http.post(url_foto(produto), {"foto": imagem("WEBP", nome="nova.webp")}, format="multipart")
    produto.refresh_from_db()
    assert not anterior.exists()
    assert (media_temporaria / produto.foto.name).exists()


def test_remover_foto(api, gerente, produto, media_temporaria):
    cliente_http = api(gerente)
    cliente_http.post(url_foto(produto), {"foto": imagem()}, format="multipart")
    produto.refresh_from_db()
    arquivo = media_temporaria / produto.foto.name

    assert cliente_http.delete(url_foto(produto)).status_code == 204
    produto.refresh_from_db()
    assert not produto.foto
    assert not arquivo.exists()
    assert cliente_http.get(f"/api/produtos/{produto.pk}/").data["foto"] is None


def test_arquivo_que_nao_e_imagem_e_recusado(api, gerente, produto):
    falso = SimpleUploadedFile("foto.png", b"<script>alert(1)</script>", content_type="image/png")
    resposta = api(gerente).post(url_foto(produto), {"foto": falso}, format="multipart")
    assert resposta.status_code == 400
    assert "não é uma imagem válida" in resposta.data["foto"][0]


def test_formato_nao_aceito_e_recusado(api, gerente, produto):
    gif = imagem("GIF", nome="animada.gif")
    resposta = api(gerente).post(url_foto(produto), {"foto": gif}, format="multipart")
    assert resposta.status_code == 400
    assert "JPEG, PNG ou WebP" in resposta.data["foto"][0]


def test_arquivo_acima_do_limite_e_recusado(api, gerente, produto, settings):
    settings.FOTO_PRODUTO_MAX_BYTES = 100
    resposta = api(gerente).post(url_foto(produto), {"foto": imagem()}, format="multipart")
    assert resposta.status_code == 400
    assert "no máximo" in resposta.data["foto"][0]


def test_resolucao_absurda_e_recusada(api, gerente, produto, monkeypatch):
    monkeypatch.setattr("apps.produtos.fotos.MAX_PIXELS", 100)
    resposta = api(gerente).post(url_foto(produto), {"foto": imagem()}, format="multipart")
    assert resposta.status_code == 400
    assert MAX_PIXELS > 100  # o limite real continua alto para fotos comuns


def test_sem_arquivo_e_recusado(api, gerente, produto):
    assert api(gerente).post(url_foto(produto), {}, format="multipart").status_code == 400


def test_somente_gestao_altera_foto(api, caixa, separador, produto):
    for usuario in (caixa, separador):
        cliente_http = api(usuario)
        assert cliente_http.post(url_foto(produto), {"foto": imagem()}, format="multipart").status_code == 403
        assert cliente_http.delete(url_foto(produto)).status_code == 403


def test_foto_nao_e_alterada_pelo_json_do_produto(api, gerente, produto):
    resposta = api(gerente).patch(f"/api/produtos/{produto.pk}/", {"foto": "../../etc/passwd"}, format="json")
    assert resposta.status_code == 200
    produto.refresh_from_db()
    assert not produto.foto

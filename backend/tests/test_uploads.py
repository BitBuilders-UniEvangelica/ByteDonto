"""Uploads: tipo real pelo conteúdo (magic bytes), limite, nomes únicos, links assinados."""

import io

import pytest

from conftest import auth
from app.imagens.routes import detectar_mime, SIGNED_URL_TTL, BUCKET

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 32
GIF = b"GIF89a" + b"\x00" * 32
WEBP = b"RIFF\x24\x00\x00\x00WEBPVP8 " + b"\x00" * 32
PDF = b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n" + b"0" * 32


def _upload(client, cenario, conteudo, nome, tipo="imagem", token=None, mimetype=None):
    arquivo = (io.BytesIO(conteudo), nome, mimetype) if mimetype else (io.BytesIO(conteudo), nome)
    return client.post(
        "/api/imagens/upload",
        headers=auth(token or cenario.espec.token),
        data={"paciente_id": cenario.paciente["id"], "tipo": tipo, "file": arquivo},
        content_type="multipart/form-data",
    )


@pytest.mark.parametrize("conteudo,mime", [
    (PNG, "image/png"), (JPEG, "image/jpeg"), (GIF, "image/gif"),
    (WEBP, "image/webp"), (PDF, "application/pdf"),
    (b"<html><script>alert(1)</script>", None), (b"MZ\x90\x00", None),
    (b"RIFF\x00\x00\x00\x00WAVE", None), (b"", None),
])
def test_detectar_mime(conteudo, mime):
    assert detectar_mime(conteudo) == mime


@pytest.mark.parametrize("conteudo,nome,mime", [
    (PNG, "rx.png", "image/png"), (JPEG, "foto.jpg", "image/jpeg"), (JPEG, "foto.JPEG", "image/jpeg"),
    (GIF, "a.gif", "image/gif"), (WEBP, "a.webp", "image/webp"), (PDF, "laudo.pdf", "application/pdf"),
])
def test_upload_valido_usa_mime_do_servidor(client, cenario, db, conteudo, nome, mime):
    # O cliente mente no Content-Type: o servidor ignora e usa o detectado.
    r = _upload(client, cenario, conteudo, nome, mimetype="text/html")
    assert r.status_code == 201, r.get_json()
    (path, salvo), = db.storage.items()
    assert salvo["opcoes"]["content-type"] == mime
    assert salvo["bucket"] == BUCKET
    assert salvo["bytes"] == conteudo


@pytest.mark.parametrize("conteudo,nome", [
    (b"<html><script>alert(1)</script></html>", "rx.png"),   # HTML disfarçado
    (b"MZ\x90\x00\x03\x00\x00\x00", "laudo.pdf"),           # executável disfarçado
    (PNG, "rx.pdf"),                                         # extensão incompatível
    (PDF, "laudo.jpg"),
    (JPEG, "foto.png"),
    (b"texto qualquer", "nota.gif"),
])
def test_conteudo_incompativel_e_rejeitado(client, cenario, db, conteudo, nome):
    r = _upload(client, cenario, conteudo, nome, mimetype="image/png")
    assert r.status_code == 400
    assert db.storage == {} and len(db.tabelas["paciente_imagens"]) == 2


@pytest.mark.parametrize("nome", ["virus.exe", "script.svg", "pagina.html", "semextensao"])
def test_extensao_nao_permitida(client, cenario, db, nome):
    assert _upload(client, cenario, PNG, nome).status_code == 400
    assert db.storage == {}


def test_arquivo_vazio(client, cenario, db):
    assert _upload(client, cenario, b"", "rx.png").status_code == 400


def test_limite_de_10mb(client, cenario, db):
    limite = 10 * 1024 * 1024
    ok = _upload(client, cenario, PNG + b"\x00" * (limite - len(PNG)), "grande.png")
    assert ok.status_code == 201
    db.storage.clear()
    r = _upload(client, cenario, PNG + b"\x00" * (limite - len(PNG) + 1), "grande.png")
    assert r.status_code == 400
    r = _upload(client, cenario, PNG + b"\x00" * (12 * 1024 * 1024), "enorme.png")
    assert r.status_code == 413
    assert db.storage == {}


def test_nomes_unicos_sem_nome_do_cliente(client, cenario, db):
    nome_malicioso = "../../outra-clinica/../rx.png"
    for _ in range(2):
        assert _upload(client, cenario, PNG, nome_malicioso).status_code == 201
    paths = list(db.storage)
    assert len(set(paths)) == 2
    for p in paths:
        assert p.startswith(f"{cenario.clinica_a}/{cenario.paciente['id']}/")
        assert ".." not in p and "outra-clinica" not in p
        assert p.endswith(".png")


def test_link_assinado_de_uma_hora(client, cenario, db):
    assert SIGNED_URL_TTL == 3600
    r = _upload(client, cenario, PNG, "rx.png")
    assert "ttl=3600" in r.get_json()["url"]
    lista = client.get(f"/api/imagens/?paciente_id={cenario.paciente['id']}", headers=auth(cenario.espec.token))
    assert all("ttl=3600" in i["url"] for i in lista.get_json())
    # Não persiste URL pública: só o storage_path
    registro = db.tabelas["paciente_imagens"][-1]
    assert "url" not in registro and registro["storage_path"]

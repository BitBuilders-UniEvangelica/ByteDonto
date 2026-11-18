"""Uploads com storage real (modo local): magic bytes, limite, nomes únicos,
links assinados de 1 hora e entrega segura do arquivo."""

import io
import os
import time

import jwt
import pytest

from apoio import auth, consultar

pytestmark = pytest.mark.rotas

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 32
GIF = b"GIF89a" + b"\x00" * 32
WEBP = b"RIFF\x24\x00\x00\x00WEBPVP8 " + b"\x00" * 32
PDF = b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n" + b"0" * 32


@pytest.fixture
def ctx(cenario):
    dono = cenario.dono()
    espec = cenario.membro(dono, "Especialista")
    return dono, espec, cenario.paciente(dono)


def _upload(client, quem, paciente, conteudo, nome, tipo="imagem", mimetype=None):
    arquivo = (io.BytesIO(conteudo), nome, mimetype) if mimetype else (io.BytesIO(conteudo), nome)
    return client.post("/api/imagens/upload", headers=auth(quem["token"]), content_type="multipart/form-data",
                       data={"paciente_id": paciente["id"], "tipo": tipo, "file": arquivo})


def _arquivos():
    from config import Config
    raiz = os.path.join(Config.STORAGE_DIR, "paciente-imagens")
    achados = []
    for pasta, _, nomes in os.walk(raiz):
        achados += [os.path.relpath(os.path.join(pasta, n), raiz) for n in nomes]
    return achados


@pytest.fixture
def opcoes_gravadas(monkeypatch):
    """Registra as opções que a ROTA passa ao storage (o content-type decidido
    pelo servidor), sem substituir a gravação real em disco."""
    from app.providers import local
    gravadas = []
    original = local._Bucket.upload

    def espiao(self, path, file, file_options=None):
        gravadas.append(dict(file_options or {}))
        return original(self, path, file, file_options)

    monkeypatch.setattr(local._Bucket, "upload", espiao)
    return gravadas


@pytest.mark.parametrize("conteudo,nome,mime", [
    (PNG, "rx.png", "image/png"), (JPEG, "foto.jpg", "image/jpeg"), (JPEG, "foto.JPEG", "image/jpeg"),
    (GIF, "a.gif", "image/gif"), (WEBP, "a.webp", "image/webp"), (PDF, "laudo.pdf", "application/pdf"),
])
def test_upload_valido_usa_mime_do_servidor(client, ctx, opcoes_gravadas, conteudo, nome, mime):
    _, espec, pac = ctx
    r = _upload(client, espec, pac, conteudo, nome, mimetype="text/html")  # cliente mente
    assert r.status_code == 201, r.get_json()
    assert opcoes_gravadas == [{"content-type": mime}]
    (arquivo,) = _arquivos()
    from config import Config
    with open(os.path.join(Config.STORAGE_DIR, "paciente-imagens", arquivo), "rb") as f:
        assert f.read() == conteudo


@pytest.mark.parametrize("conteudo,nome", [
    (b"<html><script>alert(1)</script></html>", "rx.png"),
    (b"MZ\x90\x00\x03\x00\x00\x00", "laudo.pdf"),
    (PNG, "rx.pdf"), (PDF, "laudo.jpg"), (JPEG, "foto.png"), (b"texto qualquer", "nota.gif"),
])
def test_conteudo_incompativel_e_rejeitado(client, ctx, conteudo, nome):
    _, espec, pac = ctx
    assert _upload(client, espec, pac, conteudo, nome, mimetype="image/png").status_code == 400
    assert _arquivos() == [] and consultar("SELECT count(*) FROM paciente_imagens")[0][0] == 0


@pytest.mark.parametrize("nome", ["virus.exe", "script.svg", "pagina.html", "semextensao"])
def test_extensao_nao_permitida(client, ctx, nome):
    _, espec, pac = ctx
    assert _upload(client, espec, pac, PNG, nome).status_code == 400
    assert _arquivos() == []


def test_arquivo_vazio(client, ctx):
    _, espec, pac = ctx
    assert _upload(client, espec, pac, b"", "rx.png").status_code == 400


def test_limite_de_10mb(client, ctx):
    _, espec, pac = ctx
    limite = 10 * 1024 * 1024
    assert _upload(client, espec, pac, PNG + b"\x00" * (limite - len(PNG)), "grande.png").status_code == 201
    assert _upload(client, espec, pac, PNG + b"\x00" * (limite - len(PNG) + 1), "grande.png").status_code == 400
    assert _upload(client, espec, pac, PNG + b"\x00" * (12 * 1024 * 1024), "enorme.png").status_code == 413
    assert len(_arquivos()) == 1


def test_nomes_unicos_sem_nome_do_cliente(client, ctx):
    dono, espec, pac = ctx
    for _ in range(2):
        assert _upload(client, espec, pac, PNG, "../../outra-clinica/../rx.png").status_code == 201
    paths = [p for (p,) in consultar("SELECT storage_path FROM paciente_imagens")]
    assert len(set(paths)) == 2
    for p in paths:
        assert p.startswith(f"{dono['clinica_id']}/{pac['id']}/")
        assert ".." not in p and "outra-clinica" not in p and p.endswith(".png")


def test_link_assinado_de_uma_hora_e_entrega_segura(client, ctx):
    from config import Config
    _, espec, pac = ctx
    url = _upload(client, espec, pac, PNG, "rx.png").get_json()["url"]
    token = url.split("token=", 1)[1]
    dados = jwt.decode(token, Config.JWT_SECRET, algorithms=["HS256"])
    assert 3590 <= dados["exp"] - time.time() <= 3600

    caminho = url.split("://", 1)[1].split("/", 1)[1]
    r = client.get("/" + caminho)
    assert r.status_code == 200 and r.data == PNG
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.mimetype == "image/png"

    # link adulterado / sem token / token de outro arquivo
    base, _ = ("/" + caminho).split("?token=")
    assert client.get(base).status_code == 403
    assert client.get(base + "?token=" + token[:-2] + "xx").status_code == 403
    outro = jwt.encode({"bucket": "paciente-imagens", "path": "outro.png", "exp": int(time.time()) + 60},
                       Config.JWT_SECRET, algorithm="HS256")
    assert client.get(base + "?token=" + outro).status_code == 403
    # token de LOGIN não abre arquivo
    assert client.get(base + "?token=" + espec["token"]).status_code == 403

    # listagem também devolve link de 1h; o banco guarda só o caminho
    lista = client.get(f"/api/imagens/?paciente_id={pac['id']}", headers=auth(espec["token"])).get_json()
    assert all("token=" in i["url"] for i in lista)
    colunas = [c for (c,) in consultar(
        "SELECT column_name FROM information_schema.columns WHERE table_name = 'paciente_imagens'")]
    assert "url" not in colunas


def test_token_de_arquivo_nao_serve_como_login(client, ctx):
    _, espec, pac = ctx
    url = _upload(client, espec, pac, PNG, "rx.png").get_json()["url"]
    token_arquivo = url.split("token=", 1)[1]
    assert client.get("/api/pacientes/", headers=auth(token_arquivo)).status_code == 401

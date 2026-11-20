"""Acesso a documentos clínicos (radiografias, laudos, termos) — API e camada
de armazenamento (storage local real; o Supabase Storage é coberto em
test_migrations_rls: bucket privado + policy restritiva)."""

import io
import time

import jwt
import pytest

from apoio import auth, consultar, executar

pytestmark = pytest.mark.documentos

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
PDF = b"%PDF-1.7\n" + b"0" * 32


@pytest.fixture
def docs(client, cenario):
    dono = cenario.dono()
    recep, espec = cenario.membro(dono, "Recepção"), cenario.membro(dono, "Especialista")
    pac = cenario.paciente(dono)
    dono_b = cenario.dono("Outra clínica")
    pac_b = cenario.paciente(dono_b)

    def enviar(quem, paciente, conteudo, nome, tipo):
        r = client.post("/api/imagens/upload", headers=auth(quem["token"]), content_type="multipart/form-data",
                        data={"paciente_id": paciente["id"], "tipo": tipo, "file": (io.BytesIO(conteudo), nome)})
        assert r.status_code == 201, r.get_json()
        return r.get_json()

    rx = enviar(espec, pac, PNG, "rx.png", "imagem")
    laudo = enviar(espec, pac, PDF, "laudo.pdf", "laudo")
    termo = enviar(recep, pac, PDF, "termo.pdf", "termo_consentimento")
    rx_b = enviar(dono_b, pac_b, PNG, "rx-b.png", "imagem")
    return dict(dono=dono, recep=recep, espec=espec, pac=pac, dono_b=dono_b, pac_b=pac_b,
                rx=rx, laudo=laudo, termo=termo, rx_b=rx_b)


def _caminho_local(url):
    """URL assinada local -> caminho relativo para o test client."""
    return "/" + url.split("://", 1)[1].split("/", 1)[1]


def _baixar(client, quem, doc):
    return client.get(f"/api/imagens/{doc['id']}/download", headers=auth(quem["token"]))


def test_download_autorizado(client, docs):
    r = _baixar(client, docs["espec"], docs["rx"])
    assert r.status_code == 200, r.get_json()
    corpo = r.get_json()
    assert corpo["expira_em_segundos"] == 3600 and corpo["tipo"] == "imagem"
    arquivo = client.get(_caminho_local(corpo["url"]))
    assert arquivo.status_code == 200 and arquivo.data == PNG
    assert arquivo.headers["X-Content-Type-Options"] == "nosniff"
    assert "no-store" in arquivo.headers["Cache-Control"]


def test_download_sem_autenticacao(client, docs):
    assert client.get(f"/api/imagens/{docs['rx']['id']}/download").status_code == 401
    assert client.get(f"/api/imagens/{docs['rx']['id']}/download", headers=auth("x.y.z")).status_code == 401
    assert client.get(f"/api/imagens/?paciente_id={docs['pac']['id']}").status_code == 401
    # o arquivo em si só sai com link assinado
    url = _baixar(client, docs["espec"], docs["rx"]).get_json()["url"]
    assert client.get(_caminho_local(url).split("?")[0]).status_code == 403


def test_download_sem_permissao(client, docs):
    # Recepção não tem ver_prontuario: imagem e laudo negados, termo liberado
    assert _baixar(client, docs["recep"], docs["rx"]).status_code == 403
    assert _baixar(client, docs["recep"], docs["laudo"]).status_code == 403
    assert _baixar(client, docs["recep"], docs["termo"]).status_code == 200
    listados = client.get(f"/api/imagens/?paciente_id={docs['pac']['id']}", headers=auth(docs["recep"]["token"])).get_json()
    assert [d["tipo"] for d in listados] == ["termo_consentimento"]


def test_documento_de_outra_clinica(client, docs):
    h = auth(docs["dono"]["token"])
    assert client.get(f"/api/imagens/{docs['rx_b']['id']}/download", headers=h).status_code == 404
    assert client.delete(f"/api/imagens/{docs['rx_b']['id']}", headers=h).status_code == 404
    assert client.get(f"/api/imagens/?paciente_id={docs['pac_b']['id']}", headers=h).get_json() == []
    r = client.post("/api/imagens/upload", headers=h, content_type="multipart/form-data", data={
        "paciente_id": docs["pac_b"]["id"], "tipo": "imagem", "file": (io.BytesIO(PNG), "x.png")})
    assert r.status_code == 403


def test_manipulacao_de_ids_e_de_caminhos(client, docs):
    h = auth(docs["dono"]["token"])
    assert client.get("/api/imagens/abc/download", headers=h).status_code == 400
    assert client.get("/api/imagens/00000000-0000-4000-8000-000000000000/download", headers=h).status_code == 404
    assert client.delete("/api/imagens/abc", headers=h).status_code == 400
    # registro adulterado no banco apontando para o arquivo de outra clínica: o link não é gerado
    executar("UPDATE paciente_imagens SET storage_path = %s WHERE id = %s",
             [consultar("SELECT storage_path FROM paciente_imagens WHERE id = %s", [docs["rx_b"]["id"]])[0][0],
              docs["rx"]["id"]])
    assert _baixar(client, docs["dono"], docs["rx"]).status_code == 404
    lista = client.get(f"/api/imagens/?paciente_id={docs['pac']['id']}", headers=h).get_json()
    assert docs["rx"]["id"] not in [d["id"] for d in lista]


def test_link_assinado_preso_ao_arquivo(client, docs):
    from config import Config
    url = _baixar(client, docs["espec"], docs["rx"]).get_json()["url"]
    caminho, token = _caminho_local(url).split("?token=")
    outro_doc = _caminho_local(_baixar(client, docs["dono_b"], docs["rx_b"]).get_json()["url"]).split("?")[0]
    assert client.get(f"{outro_doc}?token={token}").status_code == 403          # token de outro arquivo
    assert client.get(f"{caminho}?token={token[:-3]}abc").status_code == 403      # adulterado
    forjado = jwt.encode({"bucket": "paciente-imagens", "path": caminho.split("paciente-imagens/", 1)[1],
                          "exp": int(time.time()) + 60}, "chave-errada-com-mais-de-32-caracteres!!", algorithm="HS256")
    assert client.get(f"{caminho}?token={forjado}").status_code == 403           # assinado sem o segredo
    assert client.get(f"{caminho}?token={docs['espec']['token']}").status_code == 403  # token de login
    assert Config.JWT_SECRET  # (o segredo real nunca sai do servidor)


def test_url_assinada_expirada(app, client, docs):
    from app.providers.local import _Bucket
    caminho_no_bucket = consultar("SELECT storage_path FROM paciente_imagens WHERE id = %s", [docs["rx"]["id"]])[0][0]
    with app.test_request_context():
        expirada = _Bucket("paciente-imagens").create_signed_url(caminho_no_bucket, -5)["signedURL"]
    assert client.get(_caminho_local(expirada)).status_code == 403


def test_exclusao_sem_autorizacao_e_autorizada(client, docs):
    from config import Config
    import os
    assert client.delete(f"/api/imagens/{docs['rx']['id']}").status_code == 401
    assert client.delete(f"/api/imagens/{docs['rx']['id']}", headers=auth(docs["recep"]["token"])).status_code == 403
    assert client.delete(f"/api/imagens/{docs['laudo']['id']}", headers=auth(docs["recep"]["token"])).status_code == 403
    caminho = consultar("SELECT storage_path FROM paciente_imagens WHERE id = %s", [docs["rx"]["id"]])[0][0]
    arquivo = os.path.join(Config.STORAGE_DIR, "paciente-imagens", caminho)
    assert os.path.isfile(arquivo)
    url_antiga = _baixar(client, docs["espec"], docs["rx"]).get_json()["url"]
    assert client.delete(f"/api/imagens/{docs['rx']['id']}", headers=auth(docs["espec"]["token"])).status_code == 200
    assert not os.path.exists(arquivo)
    assert client.get(_caminho_local(url_antiga)).status_code == 404  # link antigo não ressuscita o arquivo
    assert _baixar(client, docs["espec"], docs["rx"]).status_code == 404


def test_operacoes_sensiveis_auditadas(client, docs):
    _baixar(client, docs["espec"], docs["laudo"])
    client.delete(f"/api/imagens/{docs['laudo']['id']}", headers=auth(docs["espec"]["token"]))
    linhas = consultar("SELECT usuario_id::text, acao, campos FROM auditoria_prontuario "
                       "WHERE tabela = 'paciente_imagens' AND registro_id = %s ORDER BY id", [docs["laudo"]["id"]])
    assert [l[1] for l in linhas] == ["INSERT", "ACESSO", "DELETE"]
    assert all(l[0] == docs["espec"]["id"] for l in linhas)
    assert linhas[2][2]["nome"]["antes"] == "laudo.pdf"
    # acesso negado não gera registro de acesso
    _baixar(client, docs["recep"], docs["rx"])
    assert consultar("SELECT count(*) FROM auditoria_prontuario WHERE acao = 'ACESSO' AND usuario_id = %s",
                     [docs["recep"]["id"]])[0][0] == 0


def test_nenhuma_url_publica_permanente_e_gravada(client, docs):
    colunas = {c for (c,) in consultar(
        "SELECT column_name FROM information_schema.columns WHERE table_name = 'paciente_imagens'")}
    assert "url" not in colunas
    for d in client.get(f"/api/imagens/?paciente_id={docs['pac']['id']}", headers=auth(docs["dono"]["token"])).get_json():
        token = d["url"].split("token=", 1)[1]
        from config import Config
        assert jwt.decode(token, Config.JWT_SECRET, algorithms=["HS256"])["exp"] - time.time() <= 3600

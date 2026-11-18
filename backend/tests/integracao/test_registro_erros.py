"""/api/auth/registro e vazamento de detalhes internos em erros (Fase 1).

Usa a auth local REAL. As falhas de infraestrutura são injetadas trocando um
método do cliente real (monkeypatch), não por um banco simulado.
"""

import pytest

from apoio import consultar

pytestmark = pytest.mark.rotas

URL = "/api/auth/registro"
VALIDO = {"nome": "Dona Clínica", "email": "dona@example.com", "password": "senha-forte-123"}


def test_cadastro_valido_cria_conta_e_perfil_dono(client):
    r = client.post(URL, json=VALIDO)
    assert r.status_code == 201
    assert "Conta criada" in r.get_json()["message"]
    assert consultar("SELECT count(*) FROM auth.users")[0][0] == 1
    assert consultar("SELECT papel, nome FROM usuarios") == [("Dono", "Dona Clínica")]


@pytest.mark.parametrize("kwargs", [
    {"data": "{isto não é json", "content_type": "application/json"},
    {"data": "", "content_type": "application/json"},
    {"data": "nome=x", "content_type": "application/x-www-form-urlencoded"},
    {"json": ["lista", "nao", "objeto"]},
    {"json": "texto"},
    {"json": None},
])
def test_corpo_invalido_retorna_400(client, kwargs):
    r = client.post(URL, **kwargs)
    assert r.status_code == 400
    assert "error" in r.get_json()
    assert consultar("SELECT count(*) FROM auth.users")[0][0] == 0


@pytest.mark.parametrize("faltando", ["nome", "email", "password"])
def test_campo_ausente_retorna_400(client, faltando):
    corpo = {k: v for k, v in VALIDO.items() if k != faltando}
    assert client.post(URL, json=corpo).status_code == 400


@pytest.mark.parametrize("campo,valor", [
    ("nome", 123), ("email", ["a@b.com"]), ("password", {"x": 1}), ("password", 12345678),
])
def test_campo_com_tipo_errado_retorna_400(client, campo, valor):
    assert client.post(URL, json={**VALIDO, campo: valor}).status_code == 400


@pytest.mark.parametrize("email", ["semarroba", "a@b", "a b@c.com", "x" * 250 + "@example.com"])
def test_email_invalido(client, email):
    assert client.post(URL, json={**VALIDO, "email": email}).status_code == 400


def test_senha_curta_e_longa(client):
    assert client.post(URL, json={**VALIDO, "password": "1234567"}).status_code == 400
    assert client.post(URL, json={**VALIDO, "password": "a" * 73}).status_code == 400


def test_email_duplicado_nao_e_revelado(client):
    primeiro = client.post(URL, json=VALIDO)
    segundo = client.post(URL, json={**VALIDO, "email": "DONA@example.com", "nome": "Outra pessoa"})
    assert segundo.status_code == primeiro.status_code == 201
    assert segundo.get_json() == primeiro.get_json()
    assert "cadastrad" not in segundo.get_json()["message"].lower()
    assert consultar("SELECT nome FROM usuarios") == [("Dona Clínica",)]


def test_erro_interno_nao_vaza_detalhes(client, monkeypatch):
    import app.auth.routes as rotas

    def falha(_attrs):
        raise Exception("connection to db-interno.local:5432 failed SECRET")

    monkeypatch.setattr(rotas.supabase_admin.auth.admin, "create_user", falha)
    r = client.post(URL, json=VALIDO)
    assert r.status_code == 500
    corpo = r.get_data(as_text=True)
    assert "db-interno" not in corpo and "SECRET" not in corpo and "5432" not in corpo
    assert set(r.get_json()) == {"error"}


def test_falha_no_perfil_desfaz_conta_do_auth(client, monkeypatch):
    import app.auth.routes as rotas
    real = rotas.supabase_admin

    class ClienteComFalhaNoPerfil:
        """Delega tudo ao cliente real, mas a gravação do perfil falha."""
        auth = real.auth
        storage = real.storage

        def table(self, nome):
            if nome == "usuarios":
                raise Exception("violates foreign key constraint usuarios_fk")
            return real.table(nome)

    monkeypatch.setattr(rotas, "supabase_admin", ClienteComFalhaNoPerfil())
    r = client.post(URL, json=VALIDO)
    assert r.status_code == 500
    assert "constraint" not in r.get_data(as_text=True)
    assert consultar("SELECT count(*) FROM auth.users")[0][0] == 0, \
        "usuário órfão no Auth bloquearia novos cadastros com o mesmo e-mail"


def test_me_nao_vaza_detalhe_do_token(client):
    r = client.get("/api/auth/me", headers={"Authorization": "Bearer invalido"})
    assert r.status_code == 401
    assert "detail" not in r.get_json()
    assert "invalid JWT" not in r.get_data(as_text=True)


def test_me_nao_vaza_detalhe_do_banco(client, cenario, monkeypatch):
    import app.auth.routes as rotas
    dono = cenario.dono()
    real = rotas.supabase

    class ClienteComFalha:
        auth = real.auth

        def table(self, nome):
            raise Exception("relation usuarios does not exist at host interno")

    monkeypatch.setattr(rotas, "supabase", ClienteComFalha())
    r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {dono['token']}"})
    assert r.status_code == 500
    assert "detail" not in r.get_json() and "relation" not in r.get_data(as_text=True)


def test_erro_generico_de_rota_nao_vaza(client, cenario, monkeypatch):
    import app.pacientes.routes as rotas
    dono = cenario.dono()

    class ClienteComFalha:
        def table(self, nome):
            raise Exception("stack interno: SELECT * FROM pacientes")

    monkeypatch.setattr(rotas, "supabase", ClienteComFalha())
    r = client.get("/api/pacientes/", headers={"Authorization": f"Bearer {dono['token']}"})
    assert r.status_code == 500
    assert r.get_json() == {"error": "Erro interno do servidor."}


def test_cadastro_seguido_de_login_cria_clinica(client):
    assert client.post(URL, json=VALIDO).status_code == 201
    r = client.post("/api/auth/login", json={"email": "dona@example.com", "password": "senha-forte-123"})
    assert r.status_code == 200, r.get_json()
    assert r.get_json()["user"]["papel"] == "Dono"
    assert r.get_json()["user"]["clinica_id"]

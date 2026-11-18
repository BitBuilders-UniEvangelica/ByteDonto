"""/api/auth/registro e vazamento de detalhes internos em erros."""

import pytest

URL = "/api/auth/registro"
VALIDO = {"nome": "Dona Clínica", "email": "dona@example.com", "password": "senha-forte-123"}


def _perfis(db):
    return db.tabelas.get("usuarios", [])


def test_cadastro_valido_cria_conta_e_perfil_dono(client, db):
    r = client.post(URL, json=VALIDO)
    assert r.status_code == 201
    assert "Conta criada" in r.get_json()["message"]
    assert len(db.auth_users) == 1
    perfil = _perfis(db)[0]
    assert perfil["papel"] == "Dono" and perfil["nome"] == "Dona Clínica"


@pytest.mark.parametrize("kwargs", [
    {"data": "{isto não é json", "content_type": "application/json"},
    {"data": "", "content_type": "application/json"},
    {"data": "nome=x", "content_type": "application/x-www-form-urlencoded"},
    {"json": ["lista", "nao", "objeto"]},
    {"json": "texto"},
    {"json": None},
])
def test_corpo_invalido_retorna_400(client, db, kwargs):
    r = client.post(URL, **kwargs)
    assert r.status_code == 400
    assert "error" in r.get_json()
    assert db.auth_users == {}


@pytest.mark.parametrize("faltando", ["nome", "email", "password"])
def test_campo_ausente_retorna_400(client, db, faltando):
    corpo = {k: v for k, v in VALIDO.items() if k != faltando}
    r = client.post(URL, json=corpo)
    assert r.status_code == 400
    assert db.auth_users == {}


@pytest.mark.parametrize("campo,valor", [
    ("nome", 123), ("email", ["a@b.com"]), ("password", {"x": 1}), ("password", 12345678),
])
def test_campo_com_tipo_errado_retorna_400(client, db, campo, valor):
    r = client.post(URL, json={**VALIDO, campo: valor})
    assert r.status_code == 400


@pytest.mark.parametrize("email", ["semarroba", "a@b", "a b@c.com", "x" * 250 + "@example.com"])
def test_email_invalido(client, db, email):
    assert client.post(URL, json={**VALIDO, "email": email}).status_code == 400


def test_senha_curta_e_longa(client, db):
    assert client.post(URL, json={**VALIDO, "password": "1234567"}).status_code == 400
    assert client.post(URL, json={**VALIDO, "password": "a" * 73}).status_code == 400


def test_email_duplicado_nao_e_revelado(client, db):
    primeiro = client.post(URL, json=VALIDO)
    segundo = client.post(URL, json={**VALIDO, "email": "DONA@example.com", "nome": "Outra pessoa"})
    assert segundo.status_code == primeiro.status_code == 201
    assert segundo.get_json() == primeiro.get_json()
    assert "cadastrad" not in segundo.get_json()["message"].lower()
    # Nenhum perfil novo foi criado e a conta existente não foi alterada
    assert len(_perfis(db)) == 1 and _perfis(db)[0]["nome"] == "Dona Clínica"


def test_erro_interno_nao_vaza_detalhes(client, db):
    db.falha_create_user = Exception("connection to db-interno.supabase:5432 failed SECRET")
    r = client.post(URL, json=VALIDO)
    assert r.status_code == 500
    corpo = r.get_data(as_text=True)
    assert "db-interno" not in corpo and "SECRET" not in corpo and "5432" not in corpo
    assert set(r.get_json()) == {"error"}


def test_falha_no_perfil_desfaz_conta_do_auth(client, db):
    db.falhas[("usuarios", "insert")] = Exception("violates foreign key constraint usuarios_fk")
    r = client.post(URL, json=VALIDO)
    assert r.status_code == 500
    assert "constraint" not in r.get_data(as_text=True)
    assert db.auth_users == {}, "usuário órfão no Auth bloquearia novos cadastros"
    assert any(c[0] == "delete_user" for c in db.chamadas)


def test_me_nao_vaza_detalhe_do_token(client, db):
    r = client.get("/api/auth/me", headers={"Authorization": "Bearer invalido"})
    assert r.status_code == 401
    assert "detail" not in r.get_json()
    assert "invalid JWT" not in r.get_data(as_text=True)


def test_me_nao_vaza_detalhe_do_banco(client, db, cenario):
    db.falhas[("usuarios", "select")] = Exception("relation usuarios does not exist at host x")
    r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {cenario.dono.token}"})
    assert r.status_code == 500
    assert "detail" not in r.get_json() and "relation" not in r.get_data(as_text=True)


def test_erro_generico_de_rota_nao_vaza(client, db, cenario):
    db.falhas[("pacientes", "select")] = Exception("stack interno: SELECT * FROM pacientes")
    r = client.get("/api/pacientes/", headers={"Authorization": f"Bearer {cenario.dono.token}"})
    assert r.status_code == 500
    assert r.get_json() == {"error": "Erro interno do servidor."}


def test_login_e_fluxo_existente_continuam_funcionando(client, db, monkeypatch):
    """O cadastro não muda o login: a conta criada continua apta a autenticar."""
    from types import SimpleNamespace
    import app.auth.routes as rotas

    assert client.post(URL, json=VALIDO).status_code == 201
    uid = next(iter(db.auth_users))

    class _Auth:
        def sign_in_with_password(self, cred):
            u = db.auth_users[uid]
            if cred["email"] != u["email"] or cred["password"] != u["password"]:
                raise Exception("invalid")
            return SimpleNamespace(user=SimpleNamespace(id=uid, email=u["email"]),
                                   session=SimpleNamespace(access_token="tok"))

    monkeypatch.setattr(rotas, "supabase_auth", SimpleNamespace(auth=_Auth()))
    r = client.post("/api/auth/login", json={"email": "dona@example.com", "password": "senha-forte-123"})
    assert r.status_code == 200, r.get_json()
    assert r.get_json()["user"]["papel"] == "Dono"
    assert r.get_json()["user"]["clinica_id"]  # clínica criada automaticamente no 1º login

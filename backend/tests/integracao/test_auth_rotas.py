"""RF-008 — autenticação e controle de acesso por perfil."""

from apoio import auth
import pytest

pytestmark = pytest.mark.rotas


def test_registro_cria_conta_de_proprietario(client):
    r = client.post("/api/auth/registro",
                    json={"nome": "Ana", "email": "ana@teste.com", "password": "senha-forte-123"})
    assert r.status_code == 201


def test_registro_com_email_repetido_nao_cria_conta_nem_revela(client):
    """Fase 1: e-mail repetido recebe a MESMA resposta do sucesso (sem enumeração),
    mas nenhuma conta nova é criada e a senha original continua valendo."""
    from apoio import consultar
    corpo = {"nome": "Ana", "email": "ana@teste.com", "password": "senha-forte-123"}
    primeiro = client.post("/api/auth/registro", json=corpo)
    segundo = client.post("/api/auth/registro", json={**corpo, "nome": "Intrusa", "password": "outra-senha-456"})
    assert primeiro.status_code == segundo.status_code == 201
    assert primeiro.get_json() == segundo.get_json()
    assert consultar("SELECT count(*) FROM auth.users")[0][0] == 1
    assert consultar("SELECT nome FROM usuarios")[0][0] == "Ana"
    assert client.post("/api/auth/login", json={"email": "ana@teste.com", "password": "outra-senha-456"}).status_code == 401
    assert client.post("/api/auth/login", json={"email": "ana@teste.com", "password": "senha-forte-123"}).status_code == 200


def test_registro_exige_senha_com_8_caracteres(client):
    r = client.post("/api/auth/registro",
                    json={"nome": "Ana", "email": "ana@teste.com", "password": "1234567"})
    assert r.status_code == 400


def test_login_do_proprietario_devolve_token_e_cria_clinica(cenario):
    dono = cenario.dono()
    assert dono["token"]
    assert dono["clinica_id"], "o login do Dono sem clínica deve criar uma automaticamente"


def test_login_com_senha_errada_e_recusado(client, cenario):
    cenario.dono()
    r = client.post("/api/auth/login", json={"email": "dono1@teste.com", "password": "senha-errada"})
    assert r.status_code == 401


def test_me_exige_token_valido(client, cenario):
    dono = cenario.dono()
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/auth/me", headers=auth("token-falso")).status_code == 401

    r = client.get("/api/auth/me", headers=auth(dono["token"]))
    assert r.status_code == 200
    assert r.get_json()["perfil"]["papel"] == "Dono"


def test_logout_invalida_o_token(client, cenario):
    dono = cenario.dono()
    assert client.post("/api/auth/logout", headers=auth(dono["token"])).status_code == 200
    assert client.get("/api/auth/me", headers=auth(dono["token"])).status_code == 401


def test_especialista_nao_acessa_financeiro(client, cenario):
    dono = cenario.dono()
    especialista = cenario.membro(dono, "Especialista")
    r = client.get("/api/financeiro/repasses", headers=auth(especialista["token"]))
    assert r.status_code == 403


def test_especialista_nao_agenda_consulta(client, cenario):
    dono = cenario.dono()
    especialista = cenario.membro(dono, "Especialista")
    paciente = cenario.paciente(dono)
    r = client.post("/api/consultas/",
                    json={"paciente_id": paciente["id"], "data_agendada": "2026-11-10T09:00:00"},
                    headers=auth(especialista["token"]))
    assert r.status_code == 403


def test_apenas_proprietario_cria_membros(client, cenario):
    dono = cenario.dono()
    recepcao = cenario.membro(dono, "Recepção")
    r = client.post("/api/usuarios/criar",
                    json={"nome": "X", "email": "x@teste.com", "senha": "senha-forte-123", "papel": "Recepção"},
                    headers=auth(recepcao["token"]))
    assert r.status_code == 403

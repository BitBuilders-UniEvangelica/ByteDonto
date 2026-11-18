"""seed_demo.py rodando de verdade no modo local (PostgreSQL de testes)."""

import pytest

import seed_demo
from apoio import consultar

pytestmark = pytest.mark.rotas

ENV_OK = {
    "APP_ENV": "development",
    "SEED_OWNER_EMAIL": "dono.demo@example.com", "SEED_OWNER_PASSWORD": "senha-dono-demo-1",
    "SEED_RECEPCAO_EMAIL": "recep.demo@example.com", "SEED_RECEPCAO_PASSWORD": "senha-recep-demo-1",
    "SEED_ESPECIALISTA_EMAIL": "espec.demo@example.com", "SEED_ESPECIALISTA_PASSWORD": "senha-espec-demo-1",
}


@pytest.fixture
def env_seed(monkeypatch):
    for k, v in ENV_OK.items():
        monkeypatch.setenv(k, v)


def test_seed_completo_e_idempotente(client, env_seed, monkeypatch, capsys):
    assert seed_demo.main() == 0
    assert consultar("SELECT count(*) FROM auth.users")[0][0] == 3
    assert sorted(p for (p,) in consultar("SELECT papel FROM usuarios")) == ["Dono", "Especialista", "Recepção"]
    assert consultar("SELECT count(*) FROM clinicas")[0][0] == 1
    assert consultar("SELECT count(*) FROM pacientes")[0][0] == 3
    saida = capsys.readouterr().out
    for k in ("SEED_OWNER_PASSWORD", "SEED_RECEPCAO_PASSWORD", "SEED_ESPECIALISTA_PASSWORD"):
        assert ENV_OK[k] not in saida, "o seed não pode imprimir senhas"

    # As contas criadas entram pela API real
    r = client.post("/api/auth/login", json={"email": "recep.demo@example.com", "password": "senha-recep-demo-1"})
    assert r.status_code == 200 and r.get_json()["user"]["papel"] == "Recepção"

    hashes = consultar("SELECT id, encrypted_password FROM auth.users ORDER BY id")
    monkeypatch.setenv("SEED_OWNER_PASSWORD", "nova-senha-que-nao-pode-ser-aplicada")
    assert seed_demo.main() == 0
    assert consultar("SELECT id, encrypted_password FROM auth.users ORDER BY id") == hashes, \
        "contas existentes nunca têm a senha redefinida"
    assert consultar("SELECT count(*) FROM clinicas")[0][0] == 1
    assert consultar("SELECT count(*) FROM pacientes")[0][0] == 3


def test_seed_nao_sobrescreve_conta_existente_de_outro_papel(client, cenario, env_seed, monkeypatch):
    recep = cenario.membro(cenario.dono(), "Recepção")
    monkeypatch.setenv("SEED_OWNER_EMAIL", recep["email"])
    antes = consultar("SELECT id, papel, clinica_id, nome FROM usuarios ORDER BY id")
    assert seed_demo.main() == 2
    assert consultar("SELECT id, papel, clinica_id, nome FROM usuarios ORDER BY id") == antes


def test_seed_bloqueado_fora_do_ambiente_local_nao_toca_no_banco(client, monkeypatch, capsys):
    monkeypatch.setenv("APP_ENV", "production")
    assert seed_demo.main() == 2
    assert "bloqueado" in capsys.readouterr().err
    assert consultar("SELECT count(*) FROM auth.users")[0][0] == 0

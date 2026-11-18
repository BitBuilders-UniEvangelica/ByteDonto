"""seed_demo.py: bloqueado em produção, sem credenciais no código, sem reset de senha."""

import os
import re

import pytest

import seed_demo
from seed_demo import SeedBloqueado, verificar_ambiente, ler_configuracao

ENV_OK = {
    "APP_ENV": "development",
    "SEED_OWNER_EMAIL": "dono.demo@example.com", "SEED_OWNER_PASSWORD": "senha-dono-demo-1",
    "SEED_RECEPCAO_EMAIL": "recep.demo@example.com", "SEED_RECEPCAO_PASSWORD": "senha-recep-demo-1",
    "SEED_ESPECIALISTA_EMAIL": "espec.demo@example.com", "SEED_ESPECIALISTA_PASSWORD": "senha-espec-demo-1",
}


@pytest.mark.parametrize("env", [
    {"APP_ENV": "production"},
    {"APP_ENV": "staging"},
    {},                                                   # default-deny
    {"APP_ENV": "development", "RAILWAY_ENVIRONMENT": "production"},
    {"APP_ENV": "development", "RAILWAY_ENVIRONMENT_NAME": "production"},
    {"APP_ENV": "local", "RAILWAY_PROJECT_ID": "abc"},
])
def test_bloqueado_fora_do_ambiente_local(env):
    with pytest.raises(SeedBloqueado):
        verificar_ambiente(env)


@pytest.mark.parametrize("app_env", ["development", "local", "DEVELOPMENT"])
def test_permitido_em_ambiente_local(app_env):
    verificar_ambiente({"APP_ENV": app_env})


def test_main_bloqueado_nao_toca_no_supabase(monkeypatch, capsys):
    monkeypatch.setenv("APP_ENV", "production")
    chamou = []
    monkeypatch.setattr("supabase.create_client", lambda *a, **k: chamou.append(1))
    assert seed_demo.main() == 2
    assert chamou == []
    assert "bloqueado" in capsys.readouterr().err


@pytest.mark.parametrize("faltando", [k for k in ENV_OK if k.startswith("SEED_")])
def test_credenciais_obrigatorias_por_variavel(faltando):
    env = {k: v for k, v in ENV_OK.items() if k != faltando}
    with pytest.raises(SeedBloqueado) as e:
        ler_configuracao(env)
    assert faltando in str(e.value)


def test_senha_curta_recusada():
    with pytest.raises(SeedBloqueado):
        ler_configuracao({**ENV_OK, "SEED_RECEPCAO_PASSWORD": "curta"})


def test_emails_repetidos_recusados():
    with pytest.raises(SeedBloqueado):
        ler_configuracao({**ENV_OK, "SEED_RECEPCAO_EMAIL": ENV_OK["SEED_OWNER_EMAIL"]})


def test_sem_senhas_ou_emails_fixos_no_codigo():
    fonte = open(seed_demo.__file__, encoding="utf-8").read()
    assert not re.search(r"@(gmail|hotmail|outlook|yahoo|bytedonto)\.", fonte, re.I)
    assert not re.search(r"(SENHA|PASSWORD)\w*\s*=\s*[\"'][^\"']+[\"']", fonte)
    assert "Bytedonto@2026" not in fonte and "@2026" not in fonte
    emails = re.findall(r"[\w.+-]+@[\w-]+\.[\w.]+", fonte)
    assert all(e.endswith("@example.com") for e in emails), emails


def test_conta_existente_nao_tem_senha_redefinida(db, monkeypatch):
    from conftest import _ClienteFake
    monkeypatch.setattr(seed_demo, "admin", _ClienteFake(db))
    db.auth_users["u1"] = {"id": "u1", "email": "real@example.com", "password": "senha-original"}
    uid, novo = seed_demo.garantir_auth_user("real@example.com", "outra-senha-qualquer")
    assert (uid, novo) == ("u1", False)
    assert db.auth_users["u1"]["password"] == "senha-original"
    assert not any(c[0] == "update_user_by_id" for c in db.chamadas)


def test_perfil_existente_nao_e_sobrescrito(db, monkeypatch):
    from conftest import _ClienteFake
    monkeypatch.setattr(seed_demo, "admin", _ClienteFake(db))
    db.linha("usuarios", id="u1", nome="Pessoa Real", papel="Dono", clinica_id="c-real", permissoes={})
    perfil = seed_demo.garantir_perfil("u1", "Ana Recepção (Demo)", "Recepção", "c-demo", {"x": True})
    assert perfil["papel"] == "Dono"
    linha = db.tabelas["usuarios"][0]
    assert linha["nome"] == "Pessoa Real" and linha["clinica_id"] == "c-real" and linha["permissoes"] == {}


def test_seed_completo_em_ambiente_local(db, monkeypatch, capsys):
    """Fluxo feliz: cria tudo; rodar de novo não duplica nem altera senhas."""
    from conftest import _ClienteFake
    for k, v in ENV_OK.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setattr("supabase.create_client", lambda *a, **k: _ClienteFake(db))

    assert seed_demo.main() == 0
    assert len(db.auth_users) == 3
    papeis = sorted(u["papel"] for u in db.tabelas["usuarios"])
    assert papeis == ["Dono", "Especialista", "Recepção"]
    assert len(db.tabelas["clinicas"]) == 1 and len(db.tabelas["pacientes"]) == 3
    saida = capsys.readouterr().out
    for k in ("SEED_OWNER_PASSWORD", "SEED_RECEPCAO_PASSWORD", "SEED_ESPECIALISTA_PASSWORD"):
        assert ENV_OK[k] not in saida, "o seed não pode imprimir senhas"

    senhas = {uid: u["password"] for uid, u in db.auth_users.items()}
    monkeypatch.setenv("SEED_OWNER_PASSWORD", "nova-senha-nao-aplicar")
    assert seed_demo.main() == 0
    assert {uid: u["password"] for uid, u in db.auth_users.items()} == senhas
    assert len(db.tabelas["clinicas"]) == 1 and len(db.tabelas["pacientes"]) == 3


def test_seed_recusa_email_de_conta_de_outro_papel(db, monkeypatch):
    from conftest import _ClienteFake
    for k, v in ENV_OK.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setattr("supabase.create_client", lambda *a, **k: _ClienteFake(db))
    db.auth_users["u1"] = {"id": "u1", "email": ENV_OK["SEED_OWNER_EMAIL"], "password": "orig"}
    db.linha("usuarios", id="u1", nome="Recepcionista real", papel="Recepção", clinica_id="c1")
    assert seed_demo.main() == 2
    assert db.tabelas["usuarios"][0]["papel"] == "Recepção"
    assert "clinicas" not in db.tabelas

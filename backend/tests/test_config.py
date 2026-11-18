"""Segredos obrigatórios: a API não sobe sem eles ou com valores inseguros."""

from types import SimpleNamespace

import pytest

import config
from config import ConfigError, validar_config

SECRET_OK = "s" * 48


def _cfg(**over):
    base = dict(
        SUPABASE_URL="https://proj.supabase.co",
        SUPABASE_KEY="service-role",
        SUPABASE_ANON_KEY="anon",
        SECRET_KEY=SECRET_OK,
    )
    base.update(over)
    return SimpleNamespace(**base)


def test_config_valida_passa():
    validar_config(_cfg())


@pytest.mark.parametrize("var", ["SUPABASE_URL", "SUPABASE_KEY", "SUPABASE_ANON_KEY", "SECRET_KEY"])
@pytest.mark.parametrize("valor", [None, "", "   "])
def test_variavel_obrigatoria_ausente(var, valor):
    with pytest.raises(ConfigError) as e:
        validar_config(_cfg(**{var: valor}))
    assert var in str(e.value)


@pytest.mark.parametrize("secret", ["dev-secret", "DEV-SECRET", "changeme", "troque-por-uma-chave-aleatoria"])
def test_secret_key_conhecida_insegura(secret):
    with pytest.raises(ConfigError):
        validar_config(_cfg(SECRET_KEY=secret))


def test_secret_key_curta():
    with pytest.raises(ConfigError):
        validar_config(_cfg(SECRET_KEY="a" * 31))
    validar_config(_cfg(SECRET_KEY="a" * 32))


@pytest.mark.parametrize("url", ["http://proj.supabase.co", "ftp://x", "proj.supabase.co"])
def test_supabase_url_sem_https(url):
    with pytest.raises(ConfigError):
        validar_config(_cfg(SUPABASE_URL=url))


def test_supabase_local_em_http_permitido():
    validar_config(_cfg(SUPABASE_URL="http://localhost:54321"))
    validar_config(_cfg(SUPABASE_URL="http://127.0.0.1:54321"))


def test_service_key_igual_anon_recusada():
    with pytest.raises(ConfigError):
        validar_config(_cfg(SUPABASE_KEY="mesma", SUPABASE_ANON_KEY="mesma"))


def test_mensagem_nao_expoe_valores():
    with pytest.raises(ConfigError) as e:
        validar_config(_cfg(SECRET_KEY="curta-mas-secreta"))
    assert "curta-mas-secreta" not in str(e.value)


def test_sem_fallback_dev_secret(tmp_path):
    """Sem SECRET_KEY no ambiente, Config.SECRET_KEY fica None (sem 'dev-secret')
    e a validação recusa. Roda em subprocesso, fora da pasta do .env local."""
    import os, subprocess, sys
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env = {k: v for k, v in os.environ.items() if k != "SECRET_KEY"}
    env["PYTHONPATH"] = raiz
    codigo = (
        "import config\n"
        "assert config.Config.SECRET_KEY is None, 'fallback encontrado'\n"
        "try:\n"
        "    config.validar_config(config.Config)\n"
        "except config.ConfigError as e:\n"
        "    assert 'SECRET_KEY' in str(e); print('BLOQUEADO')\n"
    )
    r = subprocess.run([sys.executable, "-c", codigo], cwd=tmp_path, env=env,
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert "BLOQUEADO" in r.stdout


def test_create_app_interrompe_sem_segredo(monkeypatch):
    from app import create_app
    from config import Config
    monkeypatch.setattr(Config, "SECRET_KEY", "dev-secret")
    with pytest.raises(ConfigError):
        create_app()


@pytest.mark.parametrize("env,esperado", [
    ({"APP_ENV": "production"}, "production"),
    ({"RAILWAY_ENVIRONMENT": "production"}, "production"),
    ({"RAILWAY_ENVIRONMENT_NAME": "staging"}, "production"),
    ({"APP_ENV": "development", "RAILWAY_ENVIRONMENT": "x"}, "development"),
    ({}, "development"),
])
def test_ambiente_atual(monkeypatch, env, esperado):
    for v in ("APP_ENV", "RAILWAY_ENVIRONMENT", "RAILWAY_ENVIRONMENT_NAME"):
        monkeypatch.delenv(v, raising=False)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    assert config.ambiente_atual() == esperado


def test_env_nao_versionado():
    import subprocess, os
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    rastreados = subprocess.run(["git", "ls-files", "--", ".env", ".env.*"], cwd=raiz,
                                capture_output=True, text=True).stdout.split()
    assert all(f.endswith(".env.example") for f in rastreados), rastreados
    ignorado = subprocess.run(["git", "check-ignore", "-q", ".env"], cwd=raiz)
    assert ignorado.returncode == 0


def test_env_example_lista_variaveis_sem_segredos():
    import os
    caminho = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env.example")
    linhas = dict(
        l.split("=", 1) for l in open(caminho, encoding="utf-8").read().splitlines()
        if l and not l.startswith("#") and "=" in l
    )
    for var in ("SUPABASE_URL", "SUPABASE_KEY", "SUPABASE_ANON_KEY", "SECRET_KEY", "ALLOWED_ORIGINS", "APP_ENV"):
        assert var in linhas
    for var in ("SUPABASE_KEY", "SUPABASE_ANON_KEY", "SECRET_KEY", "OPENAI_API_KEY", "EVOLUTION_API_KEY",
                "SEED_OWNER_PASSWORD", "SEED_RECEPCAO_PASSWORD", "SEED_ESPECIALISTA_PASSWORD"):
        assert linhas[var].strip() == "", f"{var} não pode ter valor no exemplo"

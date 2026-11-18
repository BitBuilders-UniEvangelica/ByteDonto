"""Configuração: segredos obrigatórios (Fase 1) e travas entre ambientes (Fase 2)."""

import os
import subprocess
import sys
import tempfile
from types import SimpleNamespace

import pytest

import config
from config import ConfigError, validar_config, problemas_url_banco_local


def _ler_texto(caminho):
    with open(caminho, encoding="utf-8") as f:
        return f.read()

SECRET_OK = "s" * 48
JWT_OK = "j" * 48
BACKEND = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _supabase(**over):
    base = dict(APP_ENV="production", DATA_BACKEND="supabase",
                SUPABASE_URL="https://proj.supabase.co", SUPABASE_KEY="service-role",
                SUPABASE_ANON_KEY="anon", SECRET_KEY=SECRET_OK)
    base.update(over)
    return SimpleNamespace(**base)


def _local(**over):
    base = dict(APP_ENV="development", DATA_BACKEND="local",
                DATABASE_URL="postgresql://u:p@localhost:5432/bytedonto_dev",
                JWT_SECRET=JWT_OK, SECRET_KEY=SECRET_OK, STORAGE_DIR="/tmp/x")
    base.update(over)
    return SimpleNamespace(**base)


# ---- modo supabase (Fase 1) ---------------------------------------------------

def test_config_supabase_valida_passa():
    validar_config(_supabase())
    validar_config(_supabase(APP_ENV="staging"))
    validar_config(_supabase(APP_ENV="homologacao"))


@pytest.mark.parametrize("var", ["SUPABASE_URL", "SUPABASE_KEY", "SUPABASE_ANON_KEY", "SECRET_KEY"])
@pytest.mark.parametrize("valor", [None, "", "   "])
def test_variavel_obrigatoria_ausente(var, valor):
    with pytest.raises(ConfigError) as e:
        validar_config(_supabase(**{var: valor}))
    assert var in str(e.value)


@pytest.mark.parametrize("secret", ["dev-secret", "DEV-SECRET", "changeme", "troque-por-uma-chave-aleatoria"])
def test_secret_key_conhecida_insegura(secret):
    with pytest.raises(ConfigError):
        validar_config(_supabase(SECRET_KEY=secret))
    with pytest.raises(ConfigError):
        validar_config(_local(SECRET_KEY=secret))


def test_secret_key_curta():
    with pytest.raises(ConfigError):
        validar_config(_supabase(SECRET_KEY="a" * 31))
    validar_config(_supabase(SECRET_KEY="a" * 32))


@pytest.mark.parametrize("url", ["http://proj.supabase.co", "ftp://x", "proj.supabase.co"])
def test_supabase_url_sem_https(url):
    with pytest.raises(ConfigError):
        validar_config(_supabase(SUPABASE_URL=url))


def test_supabase_local_em_http_permitido():
    validar_config(_supabase(SUPABASE_URL="http://localhost:54321"))
    validar_config(_supabase(SUPABASE_URL="http://127.0.0.1:54321"))


def test_service_key_igual_anon_recusada():
    with pytest.raises(ConfigError):
        validar_config(_supabase(SUPABASE_KEY="mesma", SUPABASE_ANON_KEY="mesma"))


def test_mensagem_nao_expoe_valores():
    with pytest.raises(ConfigError) as e:
        validar_config(_supabase(SECRET_KEY="curta-mas-secreta"))
    assert "curta-mas-secreta" not in str(e.value)
    with pytest.raises(ConfigError) as e:
        validar_config(_local(DATABASE_URL="postgresql://u:SENHA-SECRETA@db.abc.supabase.co:5432/postgres"))
    assert "SENHA-SECRETA" not in str(e.value) and "abc" not in str(e.value)


# ---- seleção de modo e travas entre ambientes (Fase 2) ------------------------

def test_config_local_valida_passa():
    validar_config(_local())
    validar_config(_local(APP_ENV="test", DATABASE_URL="postgresql://localhost/bytedonto_test"))
    validar_config(_local(DATABASE_URL="postgresql:///bytedonto_dev"))  # socket Unix


def test_producao_nunca_aceita_modo_local():
    with pytest.raises(ConfigError, match="não é permitido em produção"):
        validar_config(_local(APP_ENV="production"))


def test_railway_nunca_aceita_modo_local(monkeypatch):
    monkeypatch.setenv("RAILWAY_ENVIRONMENT", "staging")
    with pytest.raises(ConfigError, match="não é permitido em produção"):
        validar_config(_local(APP_ENV="development"))


@pytest.mark.parametrize("app_env", ["development", "test", "local", ""])
def test_modo_supabase_recusado_fora_de_producao_e_homologacao(app_env):
    """Um .env de desenvolvimento com credenciais copiadas de produção não conecta
    na produção: o modo supabase exige APP_ENV production/staging/homologacao."""
    with pytest.raises(ConfigError, match="DATA_BACKEND=supabase exige APP_ENV"):
        validar_config(_supabase(APP_ENV=app_env))


@pytest.mark.parametrize("app_env,esperado", [
    ("production", "supabase"), ("development", ""), ("test", ""), ("staging", ""),
])
def test_data_backend_padrao_so_em_producao(app_env, esperado):
    assert config.resolver_data_backend(None, app_env) == esperado
    assert config.resolver_data_backend("  LOCAL ", app_env) == "local"


def test_sem_data_backend_fora_de_producao_e_erro():
    with pytest.raises(ConfigError, match="DATA_BACKEND"):
        validar_config(_local(DATA_BACKEND=None))
    validar_config(_supabase(DATA_BACKEND=None))  # produção: padrão supabase (Railway sem variável nova)


def test_data_backend_invalido():
    with pytest.raises(ConfigError, match="DATA_BACKEND"):
        validar_config(_local(DATA_BACKEND="mysql"))


@pytest.mark.parametrize("url", [
    "postgresql://postgres:x@db.abcdefgh.supabase.co:5432/postgres",
    "postgresql://postgres.abc:x@aws-0-sa-east-1.pooler.supabase.com:6543/postgres",
    "postgresql://u:p@containers-us-west-1.railway.app:5432/railway",
    "postgresql://u:p@monorail.proxy.rlwy.net:12345/railway",
    "postgresql://u:p@meu-banco.abc.us-east-1.rds.amazonaws.com/db",
    "postgresql://u:p@10.0.0.5:5432/bytedonto",
    "postgresql://u:p@servidor-da-empresa:5432/bytedonto",
    "postgresql://u:p@localhost:5432/db?host=db.x.supabase.co",
    "mysql://u:p@localhost/db",
    "",
    None,
])
def test_modo_local_recusa_banco_remoto_ou_de_producao(url):
    assert problemas_url_banco_local(url)
    with pytest.raises(ConfigError):
        validar_config(_local(DATABASE_URL=url))


def test_hosts_extras_so_por_variavel_explicita(monkeypatch):
    url = "postgresql://u:p@db:5432/bytedonto_dev"
    assert problemas_url_banco_local(url)
    monkeypatch.setenv("LOCAL_DB_ALLOWED_HOSTS", "db")
    assert problemas_url_banco_local(url) == []
    # mesmo liberado, host de Supabase continua proibido
    monkeypatch.setenv("LOCAL_DB_ALLOWED_HOSTS", "db.x.supabase.co")
    assert problemas_url_banco_local("postgresql://u:p@db.x.supabase.co/postgres")


@pytest.mark.parametrize("jwt", [None, "", "dev-secret", "curto"])
def test_modo_local_exige_jwt_secret_forte(jwt):
    with pytest.raises(ConfigError, match="JWT_SECRET"):
        validar_config(_local(JWT_SECRET=jwt))


def test_modo_local_nao_exige_credenciais_supabase():
    validar_config(_local(SUPABASE_URL=None, SUPABASE_KEY=None, SUPABASE_ANON_KEY=None))


# ---- inicialização real ------------------------------------------------------

def _rodar(env_extra, codigo):
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("SUPABASE_", "RAILWAY_", "DATA_BACKEND", "APP_ENV", "DATABASE_URL",
                                "JWT_SECRET", "SECRET_KEY"))}
    env.update(env_extra, PYTHONPATH=BACKEND)
    # cwd fora do repositório: o load_dotenv() procura .env subindo a partir do
    # diretório atual e acharia o backend/.env real do desenvolvedor.
    with tempfile.TemporaryDirectory() as fora_do_repo:
        return subprocess.run([sys.executable, "-c", codigo], cwd=fora_do_repo, env=env,
                              capture_output=True, text=True)


def test_sem_fallback_dev_secret():
    r = _rodar({"APP_ENV": "production"}, (
        "import config\n"
        "assert config.Config.SECRET_KEY is None, 'fallback encontrado'\n"
        "assert config.Config.JWT_SECRET is None, 'fallback de JWT encontrado'\n"
        "try:\n"
        "    config.validar_config(config.Config)\n"
        "except config.ConfigError as e:\n"
        "    assert 'SECRET_KEY' in str(e); print('BLOQUEADO')\n"))
    assert r.returncode == 0, r.stderr
    assert "BLOQUEADO" in r.stdout


def test_app_inicia_em_modo_supabase_sem_tocar_na_rede():
    """Configuração de produção: create_app sobe (clientes criados, nenhuma
    requisição feita — nada é lido nem gravado)."""
    r = _rodar({"APP_ENV": "production", "SUPABASE_URL": "https://exemplo-homologacao.supabase.co",
                "SUPABASE_KEY": "service-role-de-teste", "SUPABASE_ANON_KEY": "anon-de-teste",
                "SECRET_KEY": SECRET_OK}, (
        "import socket\n"
        "def bloqueado(*a, **k): raise AssertionError('acesso à rede na inicialização')\n"
        "socket.create_connection = bloqueado\n"
        "socket.socket.connect = bloqueado\n"
        "from app import create_app\n"
        "from config import Config\n"
        "app = create_app()\n"
        "import app.database as db\n"
        "assert Config.DATA_BACKEND == 'supabase'\n"
        "assert type(db.supabase).__module__.startswith('supabase'), type(db.supabase)\n"
        "rotas = {r.rule for r in app.url_map.iter_rules()}\n"
        "assert '/api/estoque/itens' in rotas and '/api/esterilizacao/ciclos' in rotas\n"
        "assert not any(r.startswith('/api/storage') for r in rotas), 'storage local exposto em produção'\n"
        "print('OK', app.test_client().get('/api/health').get_json())\n"))
    assert r.returncode == 0, r.stderr[-2000:]
    assert "OK" in r.stdout and "ambiente" not in r.stdout


def test_app_inicia_em_modo_local_sem_supabase():
    r = _rodar({"APP_ENV": "development", "DATA_BACKEND": "local",
                "DATABASE_URL": "postgresql://u:p@localhost:5432/bytedonto_dev",
                "JWT_SECRET": JWT_OK, "SECRET_KEY": SECRET_OK, "SUPABASE_URL": "", "SUPABASE_KEY": "",
                "SUPABASE_ANON_KEY": ""}, (
        "import sys\n"
        "from app import create_app\n"
        "app = create_app()\n"
        "import app.database as db\n"
        "assert type(db.supabase).__name__ == 'LocalClient'\n"
        "assert 'supabase' not in sys.modules, 'modo local não pode carregar o cliente Supabase'\n"
        "rotas = {r.rule for r in app.url_map.iter_rules()}\n"
        "assert any(r.startswith('/api/storage') for r in rotas)\n"
        "print('OK', app.test_client().get('/api/health').get_json())\n"))
    assert r.returncode == 0, r.stderr[-2000:]
    assert "OK" in r.stdout and "local" in r.stdout


@pytest.mark.parametrize("env", [
    {"APP_ENV": "production", "DATA_BACKEND": "local"},
    {"APP_ENV": "development"},  # esqueceu o DATA_BACKEND
    {"APP_ENV": "development", "DATA_BACKEND": "supabase"},  # .env de dev com credencial de produção
])
def test_create_app_interrompe_configuracao_que_mistura_ambientes(env):
    base = {"SECRET_KEY": SECRET_OK, "JWT_SECRET": JWT_OK,
            "DATABASE_URL": "postgresql://u:p@localhost:5432/bytedonto_dev",
            "SUPABASE_URL": "https://exemplo.supabase.co", "SUPABASE_KEY": "s", "SUPABASE_ANON_KEY": "a"}
    r = _rodar({**base, **env}, "from app import create_app\ncreate_app()\n")
    assert r.returncode != 0
    assert "ConfigError" in r.stderr


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


# ---- arquivos de configuração -------------------------------------------------

def test_env_nao_versionado():
    rastreados = subprocess.run(["git", "ls-files", "--", ".env", ".env.*"], cwd=BACKEND,
                                capture_output=True, text=True).stdout.split()
    assert all(f.endswith(".env.example") for f in rastreados), rastreados
    assert subprocess.run(["git", "check-ignore", "-q", ".env"], cwd=BACKEND).returncode == 0
    assert subprocess.run(["git", "check-ignore", "-q", "storage/x.png"], cwd=BACKEND).returncode == 0


def test_env_example_lista_variaveis_sem_segredos():
    linhas = dict(
        l.split("=", 1) for l in _ler_texto(os.path.join(BACKEND, ".env.example")).splitlines()
        if l and not l.startswith("#") and "=" in l
    )
    for var in ("APP_ENV", "DATA_BACKEND", "SECRET_KEY", "DATABASE_URL", "JWT_SECRET", "STORAGE_DIR",
                "SUPABASE_URL", "SUPABASE_KEY", "SUPABASE_ANON_KEY", "ALLOWED_ORIGINS", "PORT"):
        assert var in linhas, var
    for var in ("SUPABASE_KEY", "SUPABASE_ANON_KEY", "SECRET_KEY", "JWT_SECRET", "OPENAI_API_KEY",
                "EVOLUTION_API_KEY", "SEED_OWNER_PASSWORD", "SEED_RECEPCAO_PASSWORD", "SEED_ESPECIALISTA_PASSWORD"):
        assert linhas[var].strip() == "", f"{var} não pode ter valor no exemplo"
    assert "SUA_SENHA" in linhas["DATABASE_URL"]  # só marcador

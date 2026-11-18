"""Configuração comum da suíte de testes do backend.

Os testes usam a IMPLEMENTAÇÃO REAL da API: create_app(), rotas, auth_utils
(RBAC), validações e a camada de dados (app.database) no modo
DATA_BACKEND=local — PostgreSQL real, auth local real (hash + JWT + sessões)
e storage local real (arquivos em disco). Nada é simulado.

Banco: TEST_DATABASE_URL (padrão postgresql://localhost:5432/bytedonto_test).
Travas (o banco de testes é APAGADO a cada execução):
  * o nome do banco precisa terminar em "_test";
  * o host precisa ser local (mesma regra do modo local da API);
  * nenhuma credencial de Supabase do .env é carregada (as variáveis são
    zeradas antes de importar o app).

Organização:
  tests/unit/        — sem banco: configuração, travas, regras puras.
  tests/integracao/  — PostgreSQL real: rotas, auth, RBAC, isolamento,
                       estoque, esterilização, uploads, seed, migrations/RLS.
"""

import os
import sys
import tempfile

import pytest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "postgresql://localhost:5432/bytedonto_test")

# Precisa vir ANTES de qualquer import do app: config.py lê o ambiente no import
# e o load_dotenv() não sobrescreve variáveis já definidas (mesmo vazias).
os.environ.update({
    "APP_ENV": "test",
    "DATA_BACKEND": "local",
    "DATABASE_URL": TEST_DATABASE_URL,
    "SECRET_KEY": "chave-secreta-de-teste-com-mais-de-32-caracteres",
    "JWT_SECRET": "jwt-de-teste-com-mais-de-32-caracteres-ok!",
    "STORAGE_DIR": tempfile.mkdtemp(prefix="bytedonto_test_storage_"),
    # Zera credenciais de produção que possam existir no backend/.env
    "SUPABASE_URL": "",
    "SUPABASE_KEY": "",
    "SUPABASE_ANON_KEY": "",
})
for _var in ("RAILWAY_ENVIRONMENT", "RAILWAY_ENVIRONMENT_NAME", "RAILWAY_PROJECT_ID"):
    os.environ.pop(_var, None)

from config import problemas_url_banco_local  # noqa: E402

_NOME_BANCO = TEST_DATABASE_URL.rsplit("/", 1)[-1].split("?", 1)[0]
if not _NOME_BANCO.endswith("_test"):
    raise RuntimeError(
        f"TEST_DATABASE_URL aponta para '{_NOME_BANCO}'. O nome do banco de testes "
        "precisa terminar em '_test', porque ele é apagado a cada execução."
    )
if problemas_url_banco_local(TEST_DATABASE_URL):
    raise RuntimeError("TEST_DATABASE_URL precisa apontar para um PostgreSQL local.")


def pytest_collection_modifyitems(items):
    """Marca cada teste com a categoria da pasta (unit / integracao)."""
    for item in items:
        caminho = str(item.fspath)
        if f"{os.sep}unit{os.sep}" in caminho:
            item.add_marker(pytest.mark.unit)
        elif f"{os.sep}integracao{os.sep}" in caminho:
            item.add_marker(pytest.mark.integracao)


@pytest.fixture(scope="session")
def app():
    from config import Config
    Config.RATELIMIT_ENABLED = False  # os testes fazem muitos logins seguidos
    Config.TESTING = True
    from app import create_app
    return create_app()


@pytest.fixture
def client(app):
    return app.test_client()


from apoio import auth, gerar_cpf  # noqa: E402,F401  (reexportados por compatibilidade)

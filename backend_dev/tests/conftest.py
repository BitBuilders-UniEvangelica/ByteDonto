"""Configuração dos testes automatizados do backend_dev.

Os testes rodam num banco PRÓPRIO (padrão: bytedonto_test), recriado do zero a
cada execução a partir do database_local.sql. O banco de desenvolvimento
(bytedonto_dev) e os dados de demonstração nunca são tocados.

Para apontar para outro servidor/usuário do PostgreSQL:
    TEST_DATABASE_URL=postgresql://USUARIO:SENHA@localhost:5432/bytedonto_test venv/bin/pytest
"""

import os
import sys
import tempfile
from urllib.parse import urlparse, urlunparse

import psycopg
import pytest
from psycopg import sql

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA_SQL = os.path.join(BASE_DIR, "database_local.sql")

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL", "postgresql://localhost:5432/bytedonto_test"
)

# Trava de segurança: o banco de testes é apagado a cada execução, então o
# nome precisa terminar em "_test" (impede apagar o bytedonto_dev por engano).
_NOME_BANCO = urlparse(TEST_DATABASE_URL).path.lstrip("/")
if not _NOME_BANCO.endswith("_test"):
    raise RuntimeError(
        f"TEST_DATABASE_URL aponta para '{_NOME_BANCO}'. O nome do banco de testes "
        "precisa terminar em '_test', porque ele é apagado a cada execução."
    )

# Precisa vir antes de qualquer import do app: config.py lê o ambiente no import
# e o load_dotenv() não sobrescreve variáveis já definidas.
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["JWT_SECRET"] = "chave-de-teste-com-mais-de-32-bytes-ok"
os.environ["STORAGE_DIR"] = tempfile.mkdtemp(prefix="bytedonto_test_storage_")
sys.path.insert(0, BASE_DIR)


def _recriar_banco():
    partes = urlparse(TEST_DATABASE_URL)
    url_admin = urlunparse(partes._replace(path="/postgres"))
    with psycopg.connect(url_admin, autocommit=True) as conn:
        conn.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(_NOME_BANCO)))
        conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(_NOME_BANCO)))
    with psycopg.connect(TEST_DATABASE_URL, autocommit=True) as conn:
        with open(SCHEMA_SQL, encoding="utf-8") as f:
            conn.execute(f.read())


@pytest.fixture(scope="session")
def app():
    _recriar_banco()

    from config import Config
    Config.RATELIMIT_ENABLED = False  # os testes fazem muitos logins seguidos
    Config.TESTING = True

    from app import create_app
    return create_app()


@pytest.fixture(autouse=True)
def banco_limpo(app):
    """Esvazia todas as tabelas antes de cada teste (cada teste começa do zero)."""
    with psycopg.connect(TEST_DATABASE_URL, autocommit=True) as conn:
        tabelas = conn.execute(
            "SELECT schemaname, tablename FROM pg_tables WHERE schemaname IN ('public', 'auth')"
        ).fetchall()
        if tabelas:
            conn.execute(
                sql.SQL("TRUNCATE {} RESTART IDENTITY CASCADE").format(
                    sql.SQL(", ").join(sql.Identifier(s, t) for s, t in tabelas)
                )
            )
    yield


@pytest.fixture
def client(app):
    return app.test_client()


# ------------------------------------------------------------
# Helpers para montar o cenário de cada teste
# ------------------------------------------------------------

def gerar_cpf(base):
    """Gera um CPF válido a partir de 9 dígitos (para cadastrar pacientes de teste)."""
    digitos = [int(c) for c in f"{base:09d}"]
    for tamanho in (9, 10):
        soma = sum(d * p for d, p in zip(digitos, range(tamanho + 1, 1, -1)))
        resto = (soma * 10) % 11
        digitos.append(0 if resto == 10 else resto)
    return "".join(map(str, digitos))


def auth(token):
    return {"Authorization": f"Bearer {token}"}


class Cenario:
    """Atalhos para criar dono, equipe e pacientes pela própria API."""

    def __init__(self, client):
        self.client = client
        self._seq = 0

    def _proximo(self):
        self._seq += 1
        return self._seq

    def login(self, email, senha):
        r = self.client.post("/api/auth/login", json={"email": email, "password": senha})
        assert r.status_code == 200, r.get_json()
        return r.get_json()

    def dono(self, nome="Dona Teste"):
        """Registra um proprietário e faz login (o login cria a clínica dele)."""
        n = self._proximo()
        email, senha = f"dono{n}@teste.com", "senha-forte-123"
        r = self.client.post("/api/auth/registro", json={"nome": nome, "email": email, "password": senha})
        assert r.status_code == 201, r.get_json()
        dados = self.login(email, senha)
        return {"token": dados["access_token"], "id": dados["user"]["id"],
                "clinica_id": dados["user"]["clinica_id"]}

    def membro(self, dono, papel="Especialista", percentual_repasse=None):
        n = self._proximo()
        email, senha = f"membro{n}@teste.com", "senha-forte-123"
        corpo = {"nome": f"{papel} {n}", "email": email, "senha": senha, "papel": papel}
        if papel == "Especialista":
            corpo["cro"] = f"CRO-GO {10000 + n}"
        r = self.client.post("/api/usuarios/criar", json=corpo, headers=auth(dono["token"]))
        assert r.status_code == 201, r.get_json()
        membro_id = r.get_json()["id"]
        if percentual_repasse is not None:
            r = self.client.put(f"/api/usuarios/{membro_id}",
                                json={"percentual_repasse": percentual_repasse},
                                headers=auth(dono["token"]))
            assert r.status_code == 200, r.get_json()
        dados = self.login(email, senha)
        return {"token": dados["access_token"], "id": membro_id}

    def paciente(self, quem, **extra):
        n = self._proximo()
        corpo = {
            "nome": f"Paciente {n}",
            "cpf": gerar_cpf(123456000 + n),
            "telefone_whatsapp": "62999990000",
            "data_nascimento": "1990-05-10",
            "anamnese": {"alergias": "Nega", "medicacoes": "Nenhuma", "condicoes": "Nenhuma"},
        }
        corpo.update(extra)
        r = self.client.post("/api/pacientes/", json=corpo, headers=auth(quem["token"]))
        assert r.status_code == 201, r.get_json()
        return r.get_json()


@pytest.fixture
def cenario(client):
    return Cenario(client)

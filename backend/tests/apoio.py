"""Helpers compartilhados pelos testes (sem efeitos colaterais no import).

O ambiente de teste (DATA_BACKEND=local, banco *_test...) é definido por
tests/conftest.py, que o pytest carrega antes deste módulo.
"""

import os
import shutil
from urllib.parse import urlparse, urlunparse

import psycopg
from psycopg import sql

TEST_DATABASE_URL = os.environ["DATABASE_URL"]
SENHA_PADRAO = "senha-forte-123"


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def gerar_cpf(base):
    """Gera um CPF válido a partir de 9 dígitos (para cadastrar pacientes de teste)."""
    digitos = [int(c) for c in f"{base:09d}"]
    for tamanho in (9, 10):
        soma = sum(d * p for d, p in zip(digitos, range(tamanho + 1, 1, -1)))
        resto = (soma * 10) % 11
        digitos.append(0 if resto == 10 else resto)
    return "".join(map(str, digitos))


def url_admin(url):
    return urlunparse(urlparse(url)._replace(path="/postgres"))


def recriar_banco(url, aplicar=True):
    nome = urlparse(url).path.lstrip("/")
    assert nome.endswith("_test"), "proteção: só bancos *_test são recriados"
    with psycopg.connect(url_admin(url), autocommit=True) as conn:
        conn.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(nome)))
        conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(nome)))
    if aplicar:
        from init_db import aplicar_schema
        with psycopg.connect(url, autocommit=True) as conn:
            aplicar_schema(conn)


def limpar_banco():
    with psycopg.connect(TEST_DATABASE_URL, autocommit=True) as conn:
        tabelas = conn.execute(
            "SELECT schemaname, tablename FROM pg_tables WHERE schemaname IN ('public', 'auth')"
        ).fetchall()
        if tabelas:
            conn.execute(sql.SQL("TRUNCATE {} RESTART IDENTITY CASCADE").format(
                sql.SQL(", ").join(sql.Identifier(s, t) for s, t in tabelas)))
    from config import Config
    if os.path.isdir(Config.STORAGE_DIR):
        shutil.rmtree(Config.STORAGE_DIR)


def consultar(query, params=None):
    """Consulta direta ao banco de testes (para conferir o que a API gravou)."""
    with psycopg.connect(TEST_DATABASE_URL, autocommit=True) as conn:
        return conn.execute(query, params).fetchall()


def executar(query, params=None):
    """Comando direto sem retorno (UPDATE/INSERT de preparação de cenário)."""
    with psycopg.connect(TEST_DATABASE_URL, autocommit=True) as conn:
        conn.execute(query, params)


def foto_do_banco():
    """Impressão digital de todas as tabelas — para provar que uma rota negada
    não alterou nada."""
    with psycopg.connect(TEST_DATABASE_URL, autocommit=True) as conn:
        tabelas = [t for (t,) in conn.execute(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename")]
        foto = {}
        for t in tabelas:
            foto[t] = conn.execute(sql.SQL(
                "SELECT count(*), md5(coalesce(string_agg(x::text, '|' ORDER BY x::text), '')) FROM {} x"
            ).format(sql.Identifier(t))).fetchone()
        return foto


class Cenario:
    """Atalhos para criar dono, equipe e pacientes pela própria API."""

    def __init__(self, client):
        self.client = client
        self._seq = 0

    def _proximo(self):
        self._seq += 1
        return self._seq

    def login(self, email, senha=SENHA_PADRAO):
        r = self.client.post("/api/auth/login", json={"email": email, "password": senha})
        assert r.status_code == 200, r.get_json()
        return r.get_json()

    def dono(self, nome="Dona Teste"):
        """Registra um proprietário e faz login (o login cria a clínica dele)."""
        n = self._proximo()
        email = f"dono{n}@teste.com"
        r = self.client.post("/api/auth/registro", json={"nome": nome, "email": email, "password": SENHA_PADRAO})
        assert r.status_code == 201, r.get_json()
        dados = self.login(email)
        return {"token": dados["access_token"], "id": dados["user"]["id"], "email": email,
                "clinica_id": dados["user"]["clinica_id"]}

    def membro(self, dono, papel="Especialista", percentual_repasse=None):
        n = self._proximo()
        email = f"membro{n}@teste.com"
        corpo = {"nome": f"{papel} {n}", "email": email, "senha": SENHA_PADRAO, "papel": papel}
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
        dados = self.login(email)
        return {"token": dados["access_token"], "id": membro_id, "email": email,
                "clinica_id": dono["clinica_id"]}

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

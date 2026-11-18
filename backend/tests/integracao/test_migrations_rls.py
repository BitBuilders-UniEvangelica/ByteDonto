"""Migrations do Supabase validadas num PostgreSQL que imita o Supabase.

Monta um banco separado (*_rls_test) com:
  * os papéis do Supabase: anon, authenticated (NOLOGIN) e service_role (BYPASSRLS);
  * os default privileges que o Supabase aplica (anon/authenticated recebem
    GRANT ALL em toda tabela e função nova do schema public);
  * o schema REAL de produção: database_completo.sql + migration_penteste.sql;
e então aplica migrations/*.sql DUAS vezes (idempotência) e confere, com
SET ROLE, o que cada papel consegue fazer.
"""

import glob
import os
from urllib.parse import urlparse

import psycopg
import pytest
from psycopg import sql

from apoio import TEST_DATABASE_URL, recriar_banco, url_admin

pytestmark = [pytest.mark.migrations, pytest.mark.banco_compartilhado]

BACKEND = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MIGRATIONS = sorted(glob.glob(os.path.join(BACKEND, "migrations", "*.sql")))
SCHEMA_PRODUCAO = [os.path.join(BACKEND, "database_completo.sql"), os.path.join(BACKEND, "migration_penteste.sql")]

TABELAS_NOVAS = [
    "equipamentos_esterilizacao", "ciclos_esterilizacao", "pacotes_esterilizados",
    "fornecedores_estoque", "itens_estoque", "lotes_estoque", "movimentacoes_estoque",
]
PAPEIS = {"anon": "NOLOGIN", "authenticated": "NOLOGIN", "service_role": "NOLOGIN BYPASSRLS"}


def _url_rls():
    partes = urlparse(TEST_DATABASE_URL)
    nome = partes.path.lstrip("/").removesuffix("_test") + "_rls_test"
    return partes._replace(path="/" + nome).geturl()


def _ler(caminho):
    with open(caminho, encoding="utf-8") as f:
        return f.read()


@pytest.fixture(scope="module")
def supabase_simulado(banco):
    url = _url_rls()
    criados = []
    with psycopg.connect(url_admin(url), autocommit=True) as conn:
        for papel, atributos in PAPEIS.items():
            if not conn.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", [papel]).fetchone():
                conn.execute(sql.SQL("CREATE ROLE {} " + atributos).format(sql.Identifier(papel)))
                criados.append(papel)
    recriar_banco(url, aplicar=False)
    with psycopg.connect(url, autocommit=True) as conn:
        conn.execute("""
            CREATE SCHEMA IF NOT EXISTS auth;
            CREATE TABLE IF NOT EXISTS auth.users (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), email TEXT);
            GRANT USAGE ON SCHEMA public TO anon, authenticated, service_role;
            ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO anon, authenticated, service_role;
            ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON FUNCTIONS TO anon, authenticated, service_role;
        """)
        for caminho in SCHEMA_PRODUCAO + MIGRATIONS + MIGRATIONS:  # 2x: idempotência
            conn.execute(_ler(caminho))
        # dados mínimos (como superusuário, igual ao SQL Editor)
        dono = conn.execute("INSERT INTO auth.users (email) VALUES ('dono@example.com') RETURNING id").fetchone()[0]
        clin_a = conn.execute("INSERT INTO clinicas (nome_fantasia, dono_id) VALUES ('A', %s) RETURNING id", [dono]).fetchone()[0]
        clin_b = conn.execute("INSERT INTO clinicas (nome_fantasia, dono_id) VALUES ('B', %s) RETURNING id", [dono]).fetchone()[0]
        conn.execute("INSERT INTO usuarios (id, nome, papel, clinica_id) VALUES (%s, 'Dono', 'Dono', %s)", [dono, clin_a])
        item = conn.execute("INSERT INTO itens_estoque (clinica_id, nome, categoria, unidade) "
                            "VALUES (%s, 'Luva', 'Material', 'cx') RETURNING id", [clin_a]).fetchone()[0]
        lote = conn.execute("INSERT INTO lotes_estoque (clinica_id, item_id, quantidade) VALUES (%s, %s, 5) "
                            "RETURNING id", [clin_a, item]).fetchone()[0]
    yield {"url": url, "dono": dono, "clinica_a": clin_a, "clinica_b": clin_b, "item": item, "lote": lote}
    with psycopg.connect(url_admin(url), autocommit=True) as conn:
        conn.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(
            sql.Identifier(urlparse(url).path.lstrip("/"))))
        for papel in criados:
            conn.execute(sql.SQL("DROP ROLE IF EXISTS {}").format(sql.Identifier(papel)))


def _como(url, papel, query, params=None):
    """Executa como o papel indicado, numa transação desfeita no final."""
    with psycopg.connect(url) as conn:
        try:
            conn.execute(sql.SQL("SET ROLE {}").format(sql.Identifier(papel)))
            cur = conn.execute(query, params)
            return cur.fetchall() if cur.description else None
        finally:
            conn.rollback()


def test_rls_habilitado_em_todas_as_tabelas_novas(supabase_simulado):
    with psycopg.connect(supabase_simulado["url"]) as conn:
        rls = dict(conn.execute(
            "SELECT relname, relrowsecurity FROM pg_class WHERE relname = ANY(%s)", [TABELAS_NOVAS]).fetchall())
        policies = conn.execute(
            "SELECT tablename, policyname, permissive, roles::text FROM pg_policies WHERE tablename = ANY(%s)",
            [TABELAS_NOVAS]).fetchall()
    assert rls == {t: True for t in TABELAS_NOVAS}
    for t in TABELAS_NOVAS:
        assert (t, "sem_acesso_direto", "RESTRICTIVE", "{public}") in policies
        assert (t, "api_servidor", "PERMISSIVE", "{service_role}") in policies


def test_tabelas_de_producao_continuam_com_rls(supabase_simulado):
    with psycopg.connect(supabase_simulado["url"]) as conn:
        linhas = conn.execute(
            "SELECT relname, relrowsecurity FROM pg_class WHERE relname = ANY(%s)",
            [["clinicas", "usuarios", "pacientes", "atendimentos", "faturamento", "paciente_imagens"]]).fetchall()
    assert linhas and all(rls for _, rls in linhas)


@pytest.mark.parametrize("papel", ["anon", "authenticated"])
@pytest.mark.parametrize("tabela", TABELAS_NOVAS)
def test_chave_publica_nao_le_nem_grava(supabase_simulado, papel, tabela):
    url = supabase_simulado["url"]
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        _como(url, papel, sql.SQL("SELECT * FROM {}").format(sql.Identifier(tabela)))
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        _como(url, papel, sql.SQL("INSERT INTO {} (clinica_id) VALUES (%s)").format(sql.Identifier(tabela)),
              [supabase_simulado["clinica_a"]])
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        _como(url, papel, sql.SQL("DELETE FROM {}").format(sql.Identifier(tabela)))


@pytest.mark.parametrize("papel", ["anon", "authenticated"])
def test_chave_publica_nao_chama_funcoes_de_estoque(supabase_simulado, papel):
    s = supabase_simulado
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        _como(s["url"], papel, "SELECT * FROM estoque_registrar_saida(%s, %s, %s, 1, CURRENT_DATE, 'x', %s, %s)",
              [s["clinica_a"], s["item"], s["lote"], s["dono"], s["dono"]])
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        _como(s["url"], papel, "SELECT * FROM estoque_registrar_entrada(%s, %s, 1, CURRENT_DATE, 'L', NULL, NULL, %s)",
              [s["clinica_a"], s["item"], s["dono"]])


def test_rls_nega_mesmo_se_alguem_conceder_grant_por_engano(supabase_simulado):
    """Defesa em profundidade: um GRANT indevido no futuro não expõe os dados,
    porque a policy RESTRICTIVE nega todas as linhas."""
    s = supabase_simulado
    with psycopg.connect(s["url"]) as conn:
        conn.execute("GRANT SELECT, INSERT ON itens_estoque TO authenticated")
        try:
            conn.execute("SET ROLE authenticated")
            assert conn.execute("SELECT count(*) FROM itens_estoque").fetchone()[0] == 0
            with pytest.raises(psycopg.errors.InsufficientPrivilege, match="row-level security"):
                conn.execute("INSERT INTO itens_estoque (clinica_id, nome, categoria, unidade) "
                             "VALUES (%s, 'X', 'Material', 'un')", [s["clinica_a"]])
        finally:
            conn.rollback()  # desfaz o GRANT


def test_service_role_da_api_acessa_e_usa_as_funcoes(supabase_simulado):
    s = supabase_simulado
    assert _como(s["url"], "service_role", "SELECT count(*) FROM itens_estoque")[0][0] == 1
    linhas = _como(s["url"], "service_role",
                   "SELECT * FROM estoque_registrar_saida(%s, %s, %s, 2, CURRENT_DATE, 'Uso', %s, %s)",
                   [s["clinica_a"], s["item"], s["lote"], s["dono"], s["dono"]])
    lote, mov = linhas[0]
    assert float(lote["quantidade"]) == 3 and mov["tipo"] == "Saída"
    with pytest.raises(psycopg.errors.RaiseException, match="SALDO_INSUFICIENTE"):
        _como(s["url"], "service_role",
              "SELECT * FROM estoque_registrar_saida(%s, %s, %s, 99, CURRENT_DATE, 'Uso', %s, %s)",
              [s["clinica_a"], s["item"], s["lote"], s["dono"], s["dono"]])
    # isolamento dentro da função: o lote não é encontrado pela clínica B
    with pytest.raises(psycopg.errors.RaiseException, match="LOTE_NAO_ENCONTRADO"):
        _como(s["url"], "service_role",
              "SELECT * FROM estoque_registrar_saida(%s, %s, %s, 1, CURRENT_DATE, 'Uso', %s, %s)",
              [s["clinica_b"], s["item"], s["lote"], s["dono"], s["dono"]])


def test_trigger_isola_clinicas_ate_para_a_service_role(supabase_simulado):
    s = supabase_simulado
    with pytest.raises(psycopg.errors.ForeignKeyViolation, match="CLINICA_DIVERGENTE"):
        _como(s["url"], "service_role",
              "INSERT INTO lotes_estoque (clinica_id, item_id, quantidade) VALUES (%s, %s, 1)",
              [s["clinica_b"], s["item"]])


def test_reaplicar_migration_nao_destroi_dados(supabase_simulado):
    s = supabase_simulado
    with psycopg.connect(s["url"], autocommit=True) as conn:
        antes = conn.execute("SELECT (SELECT count(*) FROM itens_estoque), (SELECT quantidade FROM lotes_estoque "
                             "WHERE id = %s), (SELECT count(*) FROM clinicas)", [s["lote"]]).fetchone()
        for caminho in MIGRATIONS:
            conn.execute(_ler(caminho))
        depois = conn.execute("SELECT (SELECT count(*) FROM itens_estoque), (SELECT quantidade FROM lotes_estoque "
                              "WHERE id = %s), (SELECT count(*) FROM clinicas)", [s["lote"]]).fetchone()
    assert antes == depois


def test_migrations_sao_aditivas():
    """Nenhuma migration contém comandos destrutivos sobre dados/tabelas."""
    import re
    proibidos = re.compile(r"\b(DROP\s+TABLE|DROP\s+SCHEMA|TRUNCATE|DELETE\s+FROM|ALTER\s+TABLE\s+\w+\s+DROP\s+COLUMN)\b", re.I)
    for caminho in MIGRATIONS:
        sem_comentarios = re.sub(r"--.*", "", _ler(caminho))
        assert not proibidos.search(sem_comentarios), os.path.basename(caminho)

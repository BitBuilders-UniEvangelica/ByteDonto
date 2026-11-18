"""Fixtures dos testes de integração (PostgreSQL real + app Flask real).

O banco de testes é recriado do zero no início da sessão com o MESMO caminho
do init_db.py (database_local.sql + migrations/*.sql) e esvaziado antes de
cada teste. Os dados são criados pela própria API (registro, login, cadastro),
exatamente como o frontend faz.
"""

import psycopg
import pytest

from apoio import TEST_DATABASE_URL, Cenario, limpar_banco, recriar_banco


@pytest.fixture(scope="session")
def banco(app):
    try:
        recriar_banco(TEST_DATABASE_URL)
    except psycopg.OperationalError as e:
        raise RuntimeError(
            "Não foi possível conectar no PostgreSQL de testes. Defina TEST_DATABASE_URL, ex.: "
            "postgresql://USUARIO:SENHA@localhost:5432/bytedonto_test"
        ) from e
    return TEST_DATABASE_URL


@pytest.fixture(autouse=True)
def banco_limpo(request, banco):
    """Cada teste começa do zero — exceto módulos marcados banco_compartilhado,
    que montam o cenário uma vez (fixture de módulo) e só fazem leituras/negações."""
    if request.node.get_closest_marker("banco_compartilhado") is None:
        limpar_banco()
    yield


@pytest.fixture
def cenario(client):
    return Cenario(client)

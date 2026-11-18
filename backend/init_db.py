"""
ByteDonto — cria/atualiza o banco PostgreSQL LOCAL (DATA_BACKEND=local).

Como rodar (dentro de backend/):
    venv/bin/python init_db.py           # cria o banco (se não existir) e aplica schema + migrations
    venv/bin/python init_db.py --reset   # APAGA todos os dados do banco local e recria do zero

Usa a DATABASE_URL do .env. Recusa qualquer banco que não seja local (mesma
validação da API: config.problemas_url_banco_local) e nunca roda em produção.

Ordem aplicada: database_local.sql (schema base + auth local) e depois
migrations/*.sql em ordem — as MESMAS migrations aplicadas no Supabase.
"""
import glob
import os
import shutil
import sys
from urllib.parse import urlparse, urlunparse

import psycopg
from psycopg import sql

from config import Config, ambiente_atual, problemas_url_banco_local, roda_no_railway

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCHEMA_SQL = os.path.join(BASE_DIR, "database_local.sql")
MIGRATIONS_DIR = os.path.join(BASE_DIR, "migrations")


def arquivos_de_schema():
    """Schema base + migrations, na ordem em que devem ser aplicados."""
    return [SCHEMA_SQL] + sorted(glob.glob(os.path.join(MIGRATIONS_DIR, "*.sql")))


def aplicar_schema(conn):
    """Aplica schema base + migrations numa conexão (autocommit). Idempotente."""
    aplicados = []
    for caminho in arquivos_de_schema():
        with open(caminho, encoding="utf-8") as f:
            conn.execute(f.read())
        aplicados.append(os.path.relpath(caminho, BASE_DIR))
    return aplicados


def main():
    reset = "--reset" in sys.argv
    url = Config.DATABASE_URL
    if ambiente_atual() == "production" or roda_no_railway():
        sys.exit("init_db.py não roda em produção.")
    problemas = problemas_url_banco_local(url)
    if problemas:
        sys.exit("DATABASE_URL recusada: " + "; ".join(problemas))

    partes = urlparse(url)
    nome_banco = partes.path.lstrip("/")
    if not nome_banco:
        sys.exit("DATABASE_URL precisa terminar com o nome do banco, ex.: .../bytedonto_dev")

    # 1. Cria o banco se ele ainda não existir (conectando no banco 'postgres')
    url_admin = urlunparse(partes._replace(path="/postgres"))
    with psycopg.connect(url_admin, autocommit=True) as conn:
        existe = conn.execute("SELECT 1 FROM pg_database WHERE datname = %s", [nome_banco]).fetchone()
        if not existe:
            conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(nome_banco)))
            print(f"[ok] Banco '{nome_banco}' criado.")
        else:
            print(f"[ok] Banco '{nome_banco}' já existe.")

    with psycopg.connect(url, autocommit=True) as conn:
        # 2. Reset opcional: derruba as tabelas do app e do auth local
        if reset:
            resposta = input(f"Isto APAGA todos os dados de '{nome_banco}' e os arquivos de storage. Digite 'sim': ")
            if resposta.strip().lower() != "sim":
                sys.exit("Cancelado.")
            conn.execute("DROP SCHEMA IF EXISTS public CASCADE")
            conn.execute("DROP SCHEMA IF EXISTS auth CASCADE")
            conn.execute("CREATE SCHEMA public")
            if os.path.isdir(Config.STORAGE_DIR):
                shutil.rmtree(Config.STORAGE_DIR)
            print("[ok] Dados apagados.")

        # 3. Aplica schema base + migrations
        for nome in aplicar_schema(conn):
            print(f"[ok] Aplicado: {nome}")

    print("\nPronto. Próximos passos:")
    print("  venv/bin/python seed_demo.py   # (opcional) dados de demonstração")
    print("  venv/bin/python run.py         # sobe a API local (porta do PORT, ex.: 8001)")


if __name__ == "__main__":
    main()

"""
ByteDonto (dev) — cria/atualiza o banco PostgreSQL local.

Como rodar (dentro de backend_dev/):
    venv/bin/python init_db.py           # cria o banco (se não existir) e aplica o schema
    venv/bin/python init_db.py --reset   # APAGA todos os dados do banco local e recria do zero

Usa a DATABASE_URL do backend_dev/.env. O banco (ex.: bytedonto_dev) é criado
automaticamente se o usuário do PostgreSQL tiver permissão (o 'postgres' tem).
"""
import os
import shutil
import sys
from urllib.parse import urlparse, urlunparse

import psycopg
from psycopg import sql

from config import Config

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCHEMA_SQL = os.path.join(BASE_DIR, "database_local.sql")


def main():
    reset = "--reset" in sys.argv
    url = Config.DATABASE_URL
    if not url:
        sys.exit("DATABASE_URL não definida. Copie .env.example para .env e ajuste.")
    if "supabase" in url.lower():
        sys.exit("DATABASE_URL aponta para o Supabase. Este script é só para o PostgreSQL local.")

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

        # 3. Aplica o schema
        with open(SCHEMA_SQL, encoding="utf-8") as f:
            conn.execute(f.read())
        print("[ok] Schema aplicado (database_local.sql).")

    print("\nPronto. Próximos passos:")
    print("  venv/bin/python seed_demo.py   # (opcional) dados de demonstração")
    print("  venv/bin/python run.py         # sobe a API dev em http://localhost:8001")


if __name__ == "__main__":
    main()

import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class Config:
    # PostgreSQL local (ambiente de desenvolvimento)
    DATABASE_URL = os.getenv("DATABASE_URL")

    # Não usadas no backend_dev — existem só para as rotas continuarem idênticas
    # às de produção (elas passam esses valores para create_client, que os ignora).
    SUPABASE_URL = None
    SUPABASE_KEY = None
    SUPABASE_ANON_KEY = None

    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")

    # Auth local: tokens JWT assinados com esta chave
    JWT_SECRET = os.getenv("JWT_SECRET") or SECRET_KEY
    JWT_EXPIRES_SECONDS = int(os.getenv("JWT_EXPIRES_SECONDS", "3600"))

    # Storage local: onde os arquivos dos pacientes são gravados
    STORAGE_DIR = os.path.abspath(os.getenv("STORAGE_DIR") or os.path.join(BASE_DIR, "storage"))
    # Usado para montar links de arquivos fora de uma requisição (ex.: scripts)
    PUBLIC_API_URL = os.getenv("PUBLIC_API_URL", "http://localhost:8001").rstrip("/")

    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    EVOLUTION_API_URL = os.getenv("EVOLUTION_API_URL")
    EVOLUTION_API_KEY = os.getenv("EVOLUTION_API_KEY")
    EVOLUTION_INSTANCE = os.getenv("EVOLUTION_INSTANCE", "byedonto")

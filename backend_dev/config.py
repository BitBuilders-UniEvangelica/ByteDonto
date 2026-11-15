import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Valores de exemplo (antigos padrões e o .env.example) que não valem como chave real.
CHAVES_DE_EXEMPLO = {"dev-secret", "troque-por-uma-chave-aleatoria"}


class Config:
    # PostgreSQL local (ambiente de desenvolvimento)
    DATABASE_URL = os.getenv("DATABASE_URL")

    # Não usadas no backend_dev — existem só para as rotas continuarem idênticas
    # às de produção (elas passam esses valores para create_client, que os ignora).
    SUPABASE_URL = None
    SUPABASE_KEY = None
    SUPABASE_ANON_KEY = None

    SECRET_KEY = os.getenv("SECRET_KEY")

    # Auth local: tokens JWT assinados com esta chave. Sem valor padrão: quem
    # conhece a chave consegue forjar o login de qualquer usuário.
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

    @classmethod
    def problemas(cls):
        """Lista o que falta no .env para a API subir com segurança."""
        erros = []
        if not cls.DATABASE_URL:
            erros.append("DATABASE_URL não definida.")
        if not cls.JWT_SECRET:
            erros.append("JWT_SECRET (ou SECRET_KEY) não definida.")
        elif cls.JWT_SECRET in CHAVES_DE_EXEMPLO or len(cls.JWT_SECRET) < 32:
            erros.append("JWT_SECRET (ou SECRET_KEY) precisa ser aleatória e ter pelo menos 32 caracteres.")
        return erros

import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")
    SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
    SECRET_KEY = os.getenv("SECRET_KEY")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    EVOLUTION_API_URL = os.getenv("EVOLUTION_API_URL")
    EVOLUTION_API_KEY = os.getenv("EVOLUTION_API_KEY")
    EVOLUTION_INSTANCE = os.getenv("EVOLUTION_INSTANCE", "byedonto")

    @classmethod
    def problemas(cls):
        """Lista o que falta no ambiente para a API subir."""
        obrigatorias = ("SUPABASE_URL", "SUPABASE_KEY", "SUPABASE_ANON_KEY")
        return [f"{nome} não definida." for nome in obrigatorias if not getattr(cls, nome)]

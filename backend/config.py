import os
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()

# Valores que já circularam como exemplo/fallback e nunca podem ser usados como segredo.
SEGREDOS_INSEGUROS = {
    "dev-secret", "secret", "changeme", "change-me", "troque-por-uma-chave-aleatoria",
    "sua-chave-secreta", "your-secret-key", "default", "password", "123456",
}
TAMANHO_MINIMO_SECRET_KEY = 32

# Hosts em que se aceita http:// (Supabase local via `supabase start`).
HOSTS_LOCAIS = {"localhost", "127.0.0.1"}


class ConfigError(RuntimeError):
    """Configuração obrigatória ausente ou insegura — a API não deve subir."""


def ambiente_atual():
    """'production' quando APP_ENV=production ou quando roda no Railway.

    O Railway sempre injeta RAILWAY_ENVIRONMENT/RAILWAY_ENVIRONMENT_NAME, então
    um deploy sem APP_ENV é tratado como produção (fail-safe).
    """
    app_env = (os.getenv("APP_ENV") or "").strip().lower()
    if app_env:
        return app_env
    if os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("RAILWAY_ENVIRONMENT_NAME"):
        return "production"
    return "development"


class Config:
    APP_ENV = ambiente_atual()
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")
    SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
    # Sem fallback: SECRET_KEY ausente interrompe a inicialização (validar_config).
    SECRET_KEY = os.getenv("SECRET_KEY")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    EVOLUTION_API_URL = os.getenv("EVOLUTION_API_URL")
    EVOLUTION_API_KEY = os.getenv("EVOLUTION_API_KEY")
    EVOLUTION_INSTANCE = os.getenv("EVOLUTION_INSTANCE", "byedonto")
    # Limite do corpo da requisição: 10 MB do arquivo + folga do multipart.
    # Acima disso o Flask responde 413 sem ler tudo para a memória.
    MAX_CONTENT_LENGTH = 11 * 1024 * 1024


def validar_config(config=Config):
    """Levanta ConfigError se algum segredo obrigatório estiver ausente ou inseguro.

    Nunca inclui o VALOR das variáveis na mensagem — apenas o nome.
    """
    problemas = []

    for nome in ("SUPABASE_URL", "SUPABASE_KEY", "SUPABASE_ANON_KEY", "SECRET_KEY"):
        valor = getattr(config, nome, None)
        if not valor or not str(valor).strip():
            problemas.append(f"{nome} não definida")

    secret = (getattr(config, "SECRET_KEY", None) or "").strip()
    if secret:
        if secret.lower() in SEGREDOS_INSEGUROS:
            problemas.append("SECRET_KEY usa um valor padrão/inseguro conhecido")
        elif len(secret) < TAMANHO_MINIMO_SECRET_KEY:
            problemas.append(
                f"SECRET_KEY deve ter no mínimo {TAMANHO_MINIMO_SECRET_KEY} caracteres"
            )

    url = (getattr(config, "SUPABASE_URL", None) or "").strip()
    if url:
        partes = urlparse(url)
        if partes.scheme == "https" and partes.hostname:
            pass
        elif partes.scheme == "http" and partes.hostname in HOSTS_LOCAIS:
            pass
        else:
            problemas.append("SUPABASE_URL deve usar https:// (http só para localhost)")

    chave_service = (getattr(config, "SUPABASE_KEY", None) or "").strip()
    chave_anon = (getattr(config, "SUPABASE_ANON_KEY", None) or "").strip()
    if chave_service and chave_service == chave_anon:
        problemas.append("SUPABASE_KEY (service role) não pode ser igual à SUPABASE_ANON_KEY")

    if problemas:
        raise ConfigError(
            "Configuração inválida — a API não foi iniciada: "
            + "; ".join(problemas)
            + ". Veja backend/.env.example."
        )

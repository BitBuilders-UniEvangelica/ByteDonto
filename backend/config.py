import os
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Valores que já circularam como exemplo/fallback e nunca podem ser usados como segredo.
SEGREDOS_INSEGUROS = {
    "dev-secret", "secret", "changeme", "change-me", "troque-por-uma-chave-aleatoria",
    "sua-chave-secreta", "your-secret-key", "default", "password", "123456",
}
TAMANHO_MINIMO_SECRET_KEY = 32

# Hosts em que se aceita http:// (Supabase local via `supabase start`).
HOSTS_LOCAIS = {"localhost", "127.0.0.1", "::1"}

# Modos de acesso a dados (DATA_BACKEND):
#   supabase — Supabase Auth + Database (PostgREST) + Storage. Produção (Railway).
#   local    — PostgreSQL local + auth local (JWT) + arquivos em disco. Desenvolvimento.
DATA_BACKENDS = {"supabase", "local"}

# Ambientes em que o modo supabase pode rodar. Fora deles (development, test,
# local...) é preciso usar DATA_BACKEND=local — assim um .env de desenvolvimento
# com credenciais copiadas de produção não conecta na produção por engano.
AMBIENTES_SUPABASE = {"production", "staging", "homologacao"}

# Trechos de host que identificam infraestrutura gerenciada/produção. O modo
# local recusa qualquer DATABASE_URL que os contenha, mesmo em hosts liberados.
MARCADORES_PRODUCAO = ("supabase", "pooler.", "railway", "rlwy.net", "amazonaws.com", "neon.tech")


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


def roda_no_railway():
    return bool(os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("RAILWAY_ENVIRONMENT_NAME")
                or os.getenv("RAILWAY_PROJECT_ID"))


def resolver_data_backend(valor, app_env):
    """DATA_BACKEND explícito vence. Sem ele: 'supabase' só em produção
    (mantém o Railway funcionando sem variável nova); fora dela, '' (inválido)."""
    valor = (valor or "").strip().lower()
    if valor:
        return valor
    return "supabase" if app_env == "production" else ""


def hosts_locais_permitidos():
    """Hosts aceitos para DATABASE_URL no modo local (padrão: só a própria máquina).

    LOCAL_DB_ALLOWED_HOSTS permite acrescentar nomes de containers (ex.: 'db')."""
    extras = {h.strip().lower() for h in (os.getenv("LOCAL_DB_ALLOWED_HOSTS") or "").split(",") if h.strip()}
    return HOSTS_LOCAIS | extras


def problemas_url_banco_local(url):
    """Lista o que impede DATABASE_URL de ser usada no modo local (vazia = ok).

    Nunca inclui a URL (que contém senha) nas mensagens."""
    if not url or not str(url).strip():
        return ["DATABASE_URL não definida"]
    partes = urlparse(str(url).strip())
    if partes.scheme not in ("postgresql", "postgres"):
        return ["DATABASE_URL deve começar com postgresql://"]
    alvo = (partes.netloc.rsplit("@", 1)[-1] + " " + partes.query).lower()
    if any(m in alvo for m in MARCADORES_PRODUCAO):
        return ["DATABASE_URL aponta para infraestrutura de produção/gerenciada — o modo local só aceita PostgreSQL local"]
    host = (partes.hostname or "").lower()
    # Sem host = socket Unix da própria máquina.
    if host and host not in hosts_locais_permitidos():
        return ["DATABASE_URL deve apontar para a própria máquina (localhost) no modo local; "
                "para containers, liste o host em LOCAL_DB_ALLOWED_HOSTS"]
    return []


class Config:
    APP_ENV = ambiente_atual()
    DATA_BACKEND = resolver_data_backend(os.getenv("DATA_BACKEND"), APP_ENV)

    # --- modo supabase -------------------------------------------------
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")
    SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

    # --- modo local ----------------------------------------------------
    DATABASE_URL = os.getenv("DATABASE_URL")
    # Assina os tokens da auth local e os links do storage local. Sem fallback.
    JWT_SECRET = os.getenv("JWT_SECRET")
    JWT_EXPIRES_SECONDS = int(os.getenv("JWT_EXPIRES_SECONDS", "3600"))
    STORAGE_DIR = os.path.abspath(os.getenv("STORAGE_DIR") or os.path.join(BASE_DIR, "storage"))
    PUBLIC_API_URL = os.getenv("PUBLIC_API_URL", "http://localhost:8001").rstrip("/")

    # --- comum ---------------------------------------------------------
    # Sem fallback: SECRET_KEY ausente interrompe a inicialização (validar_config).
    SECRET_KEY = os.getenv("SECRET_KEY")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    EVOLUTION_API_URL = os.getenv("EVOLUTION_API_URL")
    EVOLUTION_API_KEY = os.getenv("EVOLUTION_API_KEY")
    EVOLUTION_INSTANCE = os.getenv("EVOLUTION_INSTANCE", "byedonto")
    # Fuso da clínica: a agenda trabalha com HORÁRIO DE PAREDE neste fuso
    # (ver app/horarios.py). Também define o "hoje" das métricas.
    APP_TIMEZONE = os.getenv("APP_TIMEZONE", "America/Sao_Paulo")
    # Limite do corpo da requisição: 10 MB do arquivo + folga do multipart.
    # Acima disso o Flask responde 413 sem ler tudo para a memória.
    MAX_CONTENT_LENGTH = 11 * 1024 * 1024


def _problemas_segredo(nome, valor):
    valor = (valor or "").strip()
    if not valor:
        return [f"{nome} não definida"]
    if valor.lower() in SEGREDOS_INSEGUROS:
        return [f"{nome} usa um valor padrão/inseguro conhecido"]
    if len(valor) < TAMANHO_MINIMO_SECRET_KEY:
        return [f"{nome} deve ter no mínimo {TAMANHO_MINIMO_SECRET_KEY} caracteres"]
    return []


def validar_config(config=Config):
    """Levanta ConfigError se a configuração do modo escolhido estiver ausente,
    insegura ou misturar ambientes. Nunca inclui o VALOR das variáveis na mensagem."""
    problemas = []
    app_env = (getattr(config, "APP_ENV", None) or "").strip().lower()
    modo = resolver_data_backend(getattr(config, "DATA_BACKEND", None), app_env)

    if modo not in DATA_BACKENDS:
        raise ConfigError(
            "Configuração inválida — a API não foi iniciada: DATA_BACKEND deve ser "
            "'local' (desenvolvimento) ou 'supabase' (produção/homologação). "
            "Fora de produção ele é obrigatório. Veja backend/.env.example."
        )

    problemas += _problemas_segredo("SECRET_KEY", getattr(config, "SECRET_KEY", None))

    fuso = getattr(config, "APP_TIMEZONE", None) or "America/Sao_Paulo"
    try:
        from zoneinfo import ZoneInfo
        ZoneInfo(fuso)
    except Exception:
        problemas.append("APP_TIMEZONE inválido (use um nome IANA, ex.: America/Sao_Paulo)")

    if modo == "local":
        # Produção nunca roda com banco/auth/storage locais.
        if app_env == "production" or roda_no_railway():
            problemas.append("DATA_BACKEND=local não é permitido em produção (APP_ENV=production/Railway)")
        problemas += problemas_url_banco_local(getattr(config, "DATABASE_URL", None))
        problemas += _problemas_segredo("JWT_SECRET", getattr(config, "JWT_SECRET", None))
        if not (getattr(config, "STORAGE_DIR", None) or "").strip():
            problemas.append("STORAGE_DIR não definida")
    else:
        if app_env not in AMBIENTES_SUPABASE:
            problemas.append(
                f"DATA_BACKEND=supabase exige APP_ENV em {sorted(AMBIENTES_SUPABASE)} "
                f"(atual: {app_env or 'não definido'}); para desenvolvimento use DATA_BACKEND=local"
            )
        for nome in ("SUPABASE_URL", "SUPABASE_KEY", "SUPABASE_ANON_KEY"):
            valor = getattr(config, nome, None)
            if not valor or not str(valor).strip():
                problemas.append(f"{nome} não definida")

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

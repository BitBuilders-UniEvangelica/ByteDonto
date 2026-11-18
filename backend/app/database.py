"""Camada única de acesso a dados.

As rotas importam daqui e nunca sabem qual implementação está por trás:

    from app.database import supabase                 # cliente padrão (service role)
    from app.database import cliente_admin, cliente_publico

DATA_BACKEND (ver config.py) escolhe a implementação:

  supabase — supabase-py oficial: Supabase Auth, Database (PostgREST) e
             Storage. É o modo de produção (Railway) e preserva o login com
             Google, o RLS e as credenciais atuais.
  local    — app/providers/local.py: PostgreSQL local (psycopg + pool), auth
             local com JWT e arquivos em disco. Desenvolvimento e testes.

Os dois expõem a mesma interface: .table(...).select/insert/update/delete/eq...,
.rpc(nome, params), .auth (get_user, sign_in_with_password, admin.*) e
.storage.from_(bucket).

A configuração é validada (config.validar_config) em create_app ANTES deste
módulo ser importado; o modo local valida de novo ao abrir o pool.
"""

from config import Config


def modo():
    return Config.DATA_BACKEND


def _criar(chave):
    if Config.DATA_BACKEND == "local":
        from app.providers.local import create_client as criar_local
        return criar_local()
    if Config.DATA_BACKEND == "supabase":
        from supabase import create_client as criar_supabase
        return criar_supabase(Config.SUPABASE_URL, chave)
    raise RuntimeError(f"DATA_BACKEND inválido: {Config.DATA_BACKEND!r}")


def cliente_admin():
    """Cliente com privilégio de servidor (service role no Supabase).

    Ignora o RLS no Supabase: o isolamento por clínica e o RBAC são aplicados
    pelas rotas (app.auth_utils)."""
    return _criar(Config.SUPABASE_KEY)


def cliente_publico():
    """Cliente com a chave pública (anon) — usado só no login por senha."""
    return _criar(Config.SUPABASE_ANON_KEY)


# Cliente compartilhado pelas rotas.
supabase = cliente_admin()

"""A camada única de dados (app/database.py) e o isolamento das rotas."""

import os
import re

import pytest


def _ler_texto(caminho):
    with open(caminho, encoding="utf-8") as f:
        return f.read()

BACKEND = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _fontes_das_rotas():
    for pasta, _, arquivos in os.walk(os.path.join(BACKEND, "app")):
        for a in arquivos:
            if a.endswith(".py"):
                caminho = os.path.join(pasta, a)
                yield os.path.relpath(caminho, BACKEND), _ler_texto(caminho)


def test_rotas_nao_conhecem_a_implementacao_do_banco():
    """Só app/database.py escolhe o provider; nenhum outro módulo importa o
    supabase-py ou o provider local diretamente, nem cria clientes."""
    for caminho, fonte in _fontes_das_rotas():
        if caminho in ("app/database.py",) or caminho.startswith("app/providers/"):
            continue
        assert not re.search(r"^\s*(from|import)\s+supabase\b", fonte, re.M), caminho
        assert "app.providers" not in fonte, caminho
        assert "create_client(" not in fonte, caminho
        assert "SUPABASE_URL" not in fonte and "SUPABASE_KEY" not in fonte, caminho


def test_modo_local_entrega_cliente_local(monkeypatch):
    from config import Config
    import app.database as db
    monkeypatch.setattr(Config, "DATA_BACKEND", "local")
    assert type(db.cliente_admin()).__name__ == "LocalClient"
    assert type(db.cliente_publico()).__name__ == "LocalClient"


def test_modo_supabase_entrega_cliente_oficial(monkeypatch):
    from config import Config
    import app.database as db
    monkeypatch.setattr(Config, "DATA_BACKEND", "supabase")
    monkeypatch.setattr(Config, "SUPABASE_URL", "https://exemplo-homologacao.supabase.co")
    monkeypatch.setattr(Config, "SUPABASE_KEY", "service")
    monkeypatch.setattr(Config, "SUPABASE_ANON_KEY", "anon")
    cliente = db.cliente_admin()
    assert type(cliente).__module__.startswith("supabase")
    for metodo in ("table", "rpc"):
        assert callable(getattr(cliente, metodo))


def test_modo_invalido_falha(monkeypatch):
    from config import Config
    import app.database as db
    monkeypatch.setattr(Config, "DATA_BACKEND", "outro")
    with pytest.raises(RuntimeError):
        db.cliente_admin()


def test_provider_local_recusa_banco_remoto_mesmo_fora_do_create_app(monkeypatch):
    """Segunda trava: se alguém importar o provider num script e trocar a URL,
    o pool não abre conexão fora da máquina."""
    from config import Config
    from app.providers import local
    monkeypatch.setattr(Config, "DATABASE_URL", "postgresql://u:p@db.abc.supabase.co:5432/postgres")
    monkeypatch.setattr(local, "_pool", None)
    with pytest.raises(RuntimeError, match="recusou a conexão"):
        local.QueryBuilder("pacientes").select("*").execute()


def test_os_dois_clientes_expoem_a_interface_usada_pelas_rotas(monkeypatch):
    """Contrato: o que as rotas chamam existe nas duas implementações."""
    from config import Config
    import app.database as db
    usados = {"table", "rpc", "auth", "storage"}
    operacoes = {"select", "insert", "update", "delete"}
    filtros = {"eq", "neq", "gt", "gte", "lt", "lte", "in_", "order", "limit", "single",
               "maybe_single", "execute"}
    auth_usados = {"get_user", "sign_in_with_password"}
    admin_usados = {"create_user", "delete_user", "update_user_by_id", "sign_out", "list_users"}

    monkeypatch.setattr(Config, "DATA_BACKEND", "local")
    local = db.cliente_admin()
    monkeypatch.setattr(Config, "DATA_BACKEND", "supabase")
    monkeypatch.setattr(Config, "SUPABASE_URL", "https://exemplo-homologacao.supabase.co")
    monkeypatch.setattr(Config, "SUPABASE_KEY", "service")
    remoto = db.cliente_admin()
    for cliente in (local, remoto):
        assert usados <= set(dir(cliente)), type(cliente)
        assert operacoes <= set(dir(cliente.table("pacientes"))), type(cliente)
        assert filtros <= set(dir(cliente.table("pacientes").select("*"))), type(cliente)
        assert {"eq", "neq", "in_", "execute"} <= set(dir(cliente.table("pacientes").update({"a": 1})))
        assert "execute" in dir(cliente.rpc("estoque_registrar_saida", {}))
        assert auth_usados <= set(dir(cliente.auth))
        assert admin_usados <= set(dir(cliente.auth.admin))
        assert {"upload", "create_signed_url", "remove"} <= set(dir(cliente.storage.from_("b")))

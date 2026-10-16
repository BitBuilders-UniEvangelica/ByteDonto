"""Acesso ao PostgreSQL LOCAL — ambiente de desenvolvimento (backend_dev).

Em produção (pasta backend/) as rotas usam o cliente oficial do Supabase.
Aqui, este módulo expõe um cliente com a MESMA interface usada pelas rotas,
só que falando direto com o PostgreSQL da máquina:

    supabase.table("pacientes").select("*").eq("clinica_id", x).order("created_at", desc=True).execute()
    supabase.auth.sign_in_with_password({...}) / get_user(token) / admin.create_user({...}) ...
    supabase.storage.from_("bucket").upload(...) / create_signed_url(...) / remove([...])

Assim as rotas ficam praticamente idênticas às de produção (a única diferença
é importar `create_client` daqui em vez de `from supabase import create_client`).

O que cada parte substitui:
  - Tabelas (PostgREST)  -> SQL via psycopg 3, com suporte a joins do tipo
                            "pacientes(nome)" e "dentista:usuarios!dentista_id(nome)".
  - Supabase Auth        -> tabelas auth.users / auth.sessions + senha com hash
                            (werkzeug) + JWT assinado com JWT_SECRET.
  - Supabase Storage     -> arquivos em disco (STORAGE_DIR) + URL assinada servida
                            pela rota /api/storage (app/storage_local.py).
"""

import datetime
import decimal
import os
import re
import threading
import time
import uuid
from types import SimpleNamespace

import jwt
from flask import has_request_context, request
from psycopg import sql
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from psycopg_pool import ConnectionPool
from werkzeug.security import check_password_hash, generate_password_hash, safe_join

from config import Config


if not Config.DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL não definida. Copie backend_dev/.env.example para backend_dev/.env "
        "e ajuste a conexão com o PostgreSQL local."
    )

# Trava de segurança: o backend_dev nunca deve apontar para o banco de produção.
if "supabase" in Config.DATABASE_URL.lower():
    raise RuntimeError(
        "DATABASE_URL aponta para o Supabase. O backend_dev é só para o PostgreSQL local; "
        "para produção use a pasta backend/."
    )


# ============================================================
# Erros (mesmas mensagens que o Supabase devolve, para que os
# tratamentos já existentes nas rotas continuem funcionando)
# ============================================================

class APIError(Exception):
    """Erro equivalente ao postgrest.APIError do supabase-py."""


class AuthApiError(Exception):
    """Erro equivalente ao supabase_auth.errors.AuthApiError."""


class StorageException(Exception):
    """Erro equivalente ao storage3.utils.StorageException."""


# ============================================================
# Pool de conexões (aberto só no primeiro uso)
# ============================================================

_pool = None
_pool_lock = threading.Lock()


def _conexao():
    global _pool
    if _pool is None:
        with _pool_lock:
            if _pool is None:
                _pool = ConnectionPool(
                    Config.DATABASE_URL,
                    min_size=1,
                    max_size=10,
                    open=True,
                    # Mesmo fuso do Supabase: datas saem em UTC (+00:00).
                    kwargs={"row_factory": dict_row, "options": "-c TimeZone=UTC"},
                )
    return _pool.connection()


def _json_ready(valor):
    """Converte tipos do psycopg para o que o PostgREST devolveria em JSON."""
    if isinstance(valor, uuid.UUID):
        return str(valor)
    if isinstance(valor, (datetime.datetime, datetime.date, datetime.time)):
        return valor.isoformat()
    if isinstance(valor, decimal.Decimal):
        return float(valor)
    if isinstance(valor, dict):
        return {k: _json_ready(v) for k, v in valor.items()}
    if isinstance(valor, list):
        return [_json_ready(v) for v in valor]
    return valor


# ============================================================
# Metadados do schema public (colunas e chaves estrangeiras),
# usados para validar payloads e resolver os joins do select.
# ============================================================

_meta = {"colunas": None, "fks": None}
_meta_lock = threading.Lock()


def _carregar_metadados():
    with _conexao() as conn:
        colunas = {}
        for r in conn.execute(
            "SELECT table_name, column_name, data_type FROM information_schema.columns "
            "WHERE table_schema = 'public'"
        ):
            colunas.setdefault(r["table_name"], {})[r["column_name"]] = r["data_type"]

        fks = []
        for r in conn.execute(
            """
            SELECT cl.relname AS tabela, att.attname AS coluna,
                   fcl.relname AS tabela_ref, fatt.attname AS coluna_ref,
                   con.conname AS constraint
            FROM pg_constraint con
            JOIN pg_class cl       ON cl.oid = con.conrelid
            JOIN pg_namespace ns   ON ns.oid = cl.relnamespace
            JOIN pg_class fcl      ON fcl.oid = con.confrelid
            JOIN pg_namespace fns  ON fns.oid = fcl.relnamespace
            JOIN pg_attribute att  ON att.attrelid = con.conrelid AND att.attnum = con.conkey[1]
            JOIN pg_attribute fatt ON fatt.attrelid = con.confrelid AND fatt.attnum = con.confkey[1]
            WHERE con.contype = 'f'
              AND ns.nspname = 'public' AND fns.nspname = 'public'
              AND array_length(con.conkey, 1) = 1
            """
        ):
            fks.append(r)
    with _meta_lock:
        _meta["colunas"] = colunas
        _meta["fks"] = fks


def _colunas(tabela):
    if _meta["colunas"] is None or tabela not in _meta["colunas"]:
        _carregar_metadados()  # recarrega: a tabela pode ter sido criada depois do boot
    if tabela not in _meta["colunas"]:
        raise APIError(f"Could not find the table 'public.{tabela}' in the schema cache")
    return _meta["colunas"][tabela]


def _fks():
    if _meta["fks"] is None:
        _carregar_metadados()
    return _meta["fks"]


# ============================================================
# Query builder (imita postgrest-py)
# ============================================================

_EMBED_RE = re.compile(r"^(?:(\w+):)?(\w+)(?:!(\w+))?\((.*)\)$", re.S)


def _dividir_colunas(texto):
    """Divide "a, b(c, d), e" em ["a", "b(c, d)", "e"] respeitando parênteses."""
    partes, nivel, atual = [], 0, ""
    for ch in texto:
        if ch == "(":
            nivel += 1
        elif ch == ")":
            nivel -= 1
        if ch == "," and nivel == 0:
            partes.append(atual.strip())
            atual = ""
        else:
            atual += ch
    if atual.strip():
        partes.append(atual.strip())
    return partes


class APIResponse:
    def __init__(self, data, count=None):
        self.data = data
        self.count = count

    def __repr__(self):
        return f"APIResponse(data={self.data!r}, count={self.count!r})"


class QueryBuilder:
    def __init__(self, tabela):
        self._tabela = tabela
        self._operacao = "select"
        self._colunas = "*"
        self._payload = None
        self._filtros = []
        self._ordem = []
        self._limite = None
        self._modo_single = None  # None | "single" | "maybe"

    # ---- operações ---------------------------------------------------------
    def select(self, colunas="*", count=None):
        self._operacao = "select"
        self._colunas = colunas or "*"
        return self

    def insert(self, payload, **_):
        self._operacao = "insert"
        self._payload = payload
        return self

    def update(self, payload, **_):
        self._operacao = "update"
        self._payload = payload
        return self

    def delete(self, **_):
        self._operacao = "delete"
        return self

    # ---- filtros -----------------------------------------------------------
    def _filtro(self, coluna, operador, valor):
        self._filtros.append((coluna, operador, valor))
        return self

    def eq(self, coluna, valor):
        return self._filtro(coluna, "=", valor)

    def neq(self, coluna, valor):
        return self._filtro(coluna, "<>", valor)

    def gt(self, coluna, valor):
        return self._filtro(coluna, ">", valor)

    def gte(self, coluna, valor):
        return self._filtro(coluna, ">=", valor)

    def lt(self, coluna, valor):
        return self._filtro(coluna, "<", valor)

    def lte(self, coluna, valor):
        return self._filtro(coluna, "<=", valor)

    def in_(self, coluna, valores):
        return self._filtro(coluna, "in", list(valores))

    def is_(self, coluna, valor):
        return self._filtro(coluna, "is", valor)

    # ---- modificadores -----------------------------------------------------
    def order(self, coluna, desc=False, **_):
        self._ordem.append((coluna, desc))
        return self

    def limit(self, n, **_):
        self._limite = int(n)
        return self

    def single(self):
        self._modo_single = "single"
        return self

    def maybe_single(self):
        self._modo_single = "maybe"
        return self

    # ---- montagem do SQL ---------------------------------------------------
    def _where(self):
        if not self._filtros:
            return sql.SQL(""), []
        partes, params = [], []
        for coluna, operador, valor in self._filtros:
            ident = sql.Identifier(coluna)
            if operador == "in":
                if not valor:
                    partes.append(sql.SQL("FALSE"))
                    continue
                marcadores = sql.SQL(", ").join(sql.Placeholder() * len(valor))
                partes.append(sql.SQL("{} IN ({})").format(ident, marcadores))
                params.extend(valor)
            elif operador == "is" or (operador == "=" and valor is None):
                partes.append(sql.SQL("{} IS NULL").format(ident))
            else:
                partes.append(sql.SQL("{} {} %s").format(ident, sql.SQL(operador)))
                params.append(valor)
        return sql.SQL(" WHERE ") + sql.SQL(" AND ").join(partes), params

    def _valor_param(self, tipos, coluna, valor):
        if valor is not None and tipos.get(coluna) in ("jsonb", "json"):
            return Jsonb(valor)
        return valor

    def _validar_payload(self, linha, tipos):
        for coluna in linha:
            if coluna not in tipos:
                # Mesma mensagem do PostgREST — as rotas já tratam esse caso.
                raise APIError(
                    f"Could not find the '{coluna}' column of '{self._tabela}' in the schema cache"
                )

    # ---- execução ----------------------------------------------------------
    def execute(self):
        tipos = _colunas(self._tabela)
        tabela = sql.Identifier(self._tabela)

        if self._operacao == "select":
            linhas = self._executar_select(tipos)
        elif self._operacao == "insert":
            linhas = self._executar_insert(tabela, tipos)
        elif self._operacao == "update":
            linhas = self._executar_update(tabela, tipos)
        else:
            where, params = self._where()
            with _conexao() as conn:
                linhas = conn.execute(
                    sql.SQL("DELETE FROM {}{} RETURNING *").format(tabela, where), params
                ).fetchall()
            linhas = [_json_ready(l) for l in linhas]

        if self._modo_single:
            if len(linhas) > 1 or (self._modo_single == "single" and not linhas):
                raise APIError(
                    "JSON object requested, multiple (or no) rows returned "
                    f"(PGRST116: {len(linhas)} linhas)"
                )
            if not linhas:
                return None  # igual ao supabase-py: maybe_single() sem linha -> None
            return APIResponse(linhas[0])
        return APIResponse(linhas)

    def _executar_insert(self, tabela, tipos):
        linhas = self._payload if isinstance(self._payload, list) else [self._payload]
        resultado = []
        with _conexao() as conn:
            for linha in linhas:
                linha = linha or {}
                self._validar_payload(linha, tipos)
                if linha:
                    cols = list(linha.keys())
                    query = sql.SQL("INSERT INTO {} ({}) VALUES ({}) RETURNING *").format(
                        tabela,
                        sql.SQL(", ").join(map(sql.Identifier, cols)),
                        sql.SQL(", ").join(sql.Placeholder() * len(cols)),
                    )
                    params = [self._valor_param(tipos, c, linha[c]) for c in cols]
                else:
                    query = sql.SQL("INSERT INTO {} DEFAULT VALUES RETURNING *").format(tabela)
                    params = []
                resultado.extend(conn.execute(query, params).fetchall())
        return [_json_ready(l) for l in resultado]

    def _executar_update(self, tabela, tipos):
        payload = self._payload or {}
        self._validar_payload(payload, tipos)
        if not payload:
            raise APIError("Empty update payload")
        cols = list(payload.keys())
        sets = sql.SQL(", ").join(
            sql.SQL("{} = %s").format(sql.Identifier(c)) for c in cols
        )
        params = [self._valor_param(tipos, c, payload[c]) for c in cols]
        where, params_where = self._where()
        with _conexao() as conn:
            linhas = conn.execute(
                sql.SQL("UPDATE {} SET {}{} RETURNING *").format(tabela, sets, where),
                params + params_where,
            ).fetchall()
        return [_json_ready(l) for l in linhas]

    def _executar_select(self, tipos):
        simples, embeds = [], []
        for parte in _dividir_colunas(self._colunas):
            m = _EMBED_RE.match(parte)
            if m:
                alias, alvo, dica, internas = m.groups()
                embeds.append(self._resolver_embed(alias or alvo, alvo, dica, internas))
            else:
                simples.append(parte)

        # Colunas extras necessárias para montar os joins (removidas no final)
        extras = set()
        if "*" not in simples:
            for e in embeds:
                if e["coluna_local"] not in simples:
                    extras.add(e["coluna_local"])

        if "*" in simples or not simples and not embeds:
            lista = sql.SQL("*")
        else:
            lista = sql.SQL(", ").join(map(sql.Identifier, simples + sorted(extras)))

        where, params = self._where()
        query = sql.SQL("SELECT {} FROM {}{}").format(lista, sql.Identifier(self._tabela), where)
        if self._ordem:
            query += sql.SQL(" ORDER BY ") + sql.SQL(", ").join(
                sql.SQL("{} {}").format(sql.Identifier(c), sql.SQL("DESC" if d else "ASC"))
                for c, d in self._ordem
            )
        if self._limite is not None:
            query += sql.SQL(" LIMIT {}").format(sql.Literal(self._limite))

        with _conexao() as conn:
            linhas = [_json_ready(l) for l in conn.execute(query, params).fetchall()]

        for e in embeds:
            self._aplicar_embed(linhas, e)
        for linha in linhas:
            for c in extras:
                linha.pop(c, None)
        return linhas

    def _resolver_embed(self, alias, alvo, dica, internas):
        """Descobre por qual chave estrangeira juntar (igual ao PostgREST)."""
        fks = _fks()
        # muitos-para-um: esta tabela aponta para o alvo
        diretas = [f for f in fks if f["tabela"] == self._tabela and f["tabela_ref"] == alvo]
        if dica:
            diretas = [f for f in diretas if dica in (f["coluna"], f["constraint"])]
        if len(diretas) == 1:
            f = diretas[0]
            return {"alias": alias, "alvo": alvo, "internas": internas, "lista": False,
                    "coluna_local": f["coluna"], "coluna_alvo": f["coluna_ref"]}
        # um-para-muitos: o alvo aponta para esta tabela
        reversas = [f for f in fks if f["tabela"] == alvo and f["tabela_ref"] == self._tabela]
        if dica:
            reversas = [f for f in reversas if dica in (f["coluna"], f["constraint"])]
        if not diretas and len(reversas) == 1:
            f = reversas[0]
            return {"alias": alias, "alvo": alvo, "internas": internas, "lista": True,
                    "coluna_local": f["coluna_ref"], "coluna_alvo": f["coluna"]}
        if len(diretas) > 1 or len(reversas) > 1:
            raise APIError(
                f"Could not embed because more than one relationship was found for "
                f"'{self._tabela}' and '{alvo}'. Use a hint, ex.: {alvo}!coluna(...)"
            )
        raise APIError(
            f"Could not find a relationship between '{self._tabela}' and '{alvo}' in the schema cache"
        )

    def _aplicar_embed(self, linhas, e):
        chaves = {l.get(e["coluna_local"]) for l in linhas} - {None}
        internas = _dividir_colunas(e["internas"])
        precisa_chave = "*" not in internas and e["coluna_alvo"] not in internas
        colunas = ", ".join(internas + ([e["coluna_alvo"]] if precisa_chave else []))

        relacionados = []
        if chaves:
            relacionados = QueryBuilder(e["alvo"]).select(colunas).in_(e["coluna_alvo"], list(chaves)).execute().data

        mapa = {}
        for r in relacionados:
            chave = r.pop(e["coluna_alvo"]) if precisa_chave else r.get(e["coluna_alvo"])
            if e["lista"]:
                mapa.setdefault(chave, []).append(r)
            else:
                mapa[chave] = r

        for linha in linhas:
            chave = linha.get(e["coluna_local"])
            linha[e["alias"]] = mapa.get(chave, [] if e["lista"] else None)


# ============================================================
# Auth local (substitui o Supabase Auth)
# ============================================================

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _usuario_obj(r):
    return SimpleNamespace(
        id=str(r["id"]),
        email=r["email"],
        created_at=_json_ready(r.get("created_at")),
        last_sign_in_at=_json_ready(r.get("last_sign_in_at")),
        role="authenticated",
    )


def _emitir_token(user_id, email, session_id):
    agora = int(time.time())
    payload = {
        "sub": user_id,
        "email": email,
        "session_id": session_id,
        "role": "authenticated",
        "aud": "authenticated",
        "iat": agora,
        "exp": agora + Config.JWT_EXPIRES_SECONDS,
    }
    return jwt.encode(payload, Config.JWT_SECRET, algorithm="HS256")


def _decodificar_token(token, verificar_exp=True):
    try:
        return jwt.decode(
            token,
            Config.JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated",
            options={"verify_exp": verificar_exp},
        )
    except jwt.PyJWTError as e:
        raise AuthApiError(f"invalid JWT: {e}")


class _AuthAdmin:
    def create_user(self, atributos):
        email = (atributos.get("email") or "").strip().lower()
        senha = atributos.get("password") or ""
        if not _EMAIL_RE.match(email):
            raise AuthApiError("Unable to validate email address: invalid format")
        if len(senha) < 6:
            raise AuthApiError("Password should be at least 6 characters.")
        with _conexao() as conn:
            existe = conn.execute("SELECT 1 FROM auth.users WHERE email = %s", [email]).fetchone()
            if existe:
                raise AuthApiError("A user with this email address has already been registered")
            r = conn.execute(
                "INSERT INTO auth.users (email, encrypted_password, email_confirmed_at) "
                "VALUES (%s, %s, CASE WHEN %s THEN NOW() END) RETURNING *",
                [email, generate_password_hash(senha), bool(atributos.get("email_confirm"))],
            ).fetchone()
        return SimpleNamespace(user=_usuario_obj(r))

    def update_user_by_id(self, user_id, atributos):
        sets, params = [], []
        if atributos.get("password"):
            sets.append("encrypted_password = %s")
            params.append(generate_password_hash(atributos["password"]))
        if atributos.get("email"):
            sets.append("email = %s")
            params.append(atributos["email"].strip().lower())
        if not sets:
            raise AuthApiError("Nenhum atributo para atualizar")
        with _conexao() as conn:
            r = conn.execute(
                f"UPDATE auth.users SET {', '.join(sets)}, updated_at = NOW() WHERE id = %s RETURNING *",
                params + [user_id],
            ).fetchone()
        if not r:
            raise AuthApiError("User not found")
        return SimpleNamespace(user=_usuario_obj(r))

    def delete_user(self, user_id, should_soft_delete=False):
        with _conexao() as conn:
            r = conn.execute("DELETE FROM auth.users WHERE id = %s RETURNING id", [user_id]).fetchone()
        if not r:
            raise AuthApiError("User not found")

    def list_users(self, page=None, per_page=None):
        with _conexao() as conn:
            return [_usuario_obj(r) for r in conn.execute("SELECT * FROM auth.users ORDER BY created_at")]

    def get_user_by_id(self, user_id):
        with _conexao() as conn:
            r = conn.execute("SELECT * FROM auth.users WHERE id = %s", [user_id]).fetchone()
        if not r:
            raise AuthApiError("User not found")
        return SimpleNamespace(user=_usuario_obj(r))

    def sign_out(self, token, scope="global"):
        """Revoga as sessões do dono do token (scope='global') ou só esta ('local')."""
        dados = _decodificar_token(token, verificar_exp=False)
        with _conexao() as conn:
            if scope == "local":
                conn.execute(
                    "UPDATE auth.sessions SET revoked_at = NOW() WHERE id = %s AND revoked_at IS NULL",
                    [dados.get("session_id")],
                )
            else:
                conn.execute(
                    "UPDATE auth.sessions SET revoked_at = NOW() WHERE user_id = %s AND revoked_at IS NULL",
                    [dados.get("sub")],
                )


class _Auth:
    def __init__(self):
        self.admin = _AuthAdmin()

    def sign_in_with_password(self, credenciais):
        email = (credenciais.get("email") or "").strip().lower()
        senha = credenciais.get("password") or ""
        with _conexao() as conn:
            r = conn.execute("SELECT * FROM auth.users WHERE email = %s", [email]).fetchone()
            if not r or not check_password_hash(r["encrypted_password"], senha):
                raise AuthApiError("Invalid login credentials")
            sessao = conn.execute(
                "INSERT INTO auth.sessions (user_id) VALUES (%s) RETURNING id", [r["id"]]
            ).fetchone()
            conn.execute("UPDATE auth.users SET last_sign_in_at = NOW() WHERE id = %s", [r["id"]])
        user = _usuario_obj(r)
        token = _emitir_token(user.id, user.email, str(sessao["id"]))
        session = SimpleNamespace(
            access_token=token,
            token_type="bearer",
            expires_in=Config.JWT_EXPIRES_SECONDS,
            refresh_token=None,
            user=user,
        )
        return SimpleNamespace(user=user, session=session)

    def get_user(self, token=None):
        if not token:
            raise AuthApiError("Auth session missing!")
        dados = _decodificar_token(token)
        with _conexao() as conn:
            r = conn.execute(
                """
                SELECT u.* FROM auth.users u
                JOIN auth.sessions s ON s.user_id = u.id
                WHERE u.id = %s AND s.id = %s AND s.revoked_at IS NULL
                """,
                [dados.get("sub"), dados.get("session_id")],
            ).fetchone()
        if not r:
            raise AuthApiError("Session from session_id claim in JWT does not exist")
        return SimpleNamespace(user=_usuario_obj(r))

    def sign_out(self, *_args, **_kwargs):
        # No servidor não existe sessão "do cliente" para encerrar; a revogação
        # real é feita por admin.sign_out(token).
        return None


# ============================================================
# Storage local (substitui o Supabase Storage)
# ============================================================

class _Bucket:
    def __init__(self, nome):
        self.nome = nome

    def _caminho(self, path):
        base = os.path.join(Config.STORAGE_DIR, self.nome)
        destino = safe_join(base, path)
        if destino is None:
            raise StorageException(f"Caminho inválido: {path}")
        return destino

    def upload(self, path, file, file_options=None):
        destino = self._caminho(path)
        upsert = str((file_options or {}).get("upsert", "false")).lower() == "true"
        if os.path.exists(destino) and not upsert:
            raise StorageException("The resource already exists")
        os.makedirs(os.path.dirname(destino), exist_ok=True)
        conteudo = file if isinstance(file, (bytes, bytearray)) else open(file, "rb").read()
        with open(destino, "wb") as f:
            f.write(conteudo)
        return SimpleNamespace(path=path, full_path=f"{self.nome}/{path}")

    def create_signed_url(self, path, expires_in, options=None):
        if not os.path.isfile(self._caminho(path)):
            raise StorageException("Object not found")
        token = jwt.encode(
            {"bucket": self.nome, "path": path, "exp": int(time.time()) + int(expires_in)},
            Config.JWT_SECRET,
            algorithm="HS256",
        )
        base = request.host_url.rstrip("/") if has_request_context() else Config.PUBLIC_API_URL
        url = f"{base}/api/storage/{self.nome}/{path}?token={token}"
        return {"signedURL": url, "signedUrl": url}

    def remove(self, paths):
        removidos = []
        for path in paths:
            destino = self._caminho(path)
            if os.path.isfile(destino):
                os.remove(destino)
                removidos.append({"name": path})
        return removidos


class _Storage:
    def from_(self, bucket):
        return _Bucket(bucket)


# ============================================================
# Cliente
# ============================================================

class LocalClient:
    def __init__(self):
        self.auth = _Auth()
        self.storage = _Storage()

    def table(self, nome):
        return QueryBuilder(nome)

    from_ = table


def create_client(*_args, **_kwargs):
    """Mesma assinatura do supabase.create_client — URL/chave são ignoradas aqui."""
    return LocalClient()


supabase = create_client()

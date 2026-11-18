"""Infraestrutura de testes do backend (Supabase).

Os testes NUNCA tocam o Supabase real: todos os clientes `supabase` /
`supabase_admin` dos módulos são trocados por um FakeSupabase em memória, que
implementa só o subconjunto da API usado pelas rotas.

As variáveis de ambiente abaixo são definidas ANTES de importar o app, porque
config.py lê o ambiente no import (e load_dotenv não sobrescreve o que já existe).
"""

import copy
import os
import sys
import uuid
from datetime import datetime
from types import SimpleNamespace

import pytest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

os.environ["SUPABASE_URL"] = "https://teste-bytedonto.supabase.co"
os.environ["SUPABASE_KEY"] = "chave-service-role-de-teste"
os.environ["SUPABASE_ANON_KEY"] = "chave-anon-de-teste"
os.environ["SECRET_KEY"] = "chave-secreta-de-teste-com-mais-de-32-caracteres"
os.environ["APP_ENV"] = "test"
for _var in ("RAILWAY_ENVIRONMENT", "RAILWAY_ENVIRONMENT_NAME", "RAILWAY_PROJECT_ID"):
    os.environ.pop(_var, None)


# ------------------------------------------------------------------
# Fake do cliente Supabase
# ------------------------------------------------------------------

class _Resp:
    def __init__(self, data):
        self.data = data


class FakeQuery:
    def __init__(self, db, tabela):
        self.db = db
        self.tabela = tabela
        self.op = "select"
        self.filtros = []
        self.payload = None
        self.unico = None  # None | "maybe" | "single"
        self._limit = None

    # construção ------------------------------------------------------
    def select(self, *_a, **_k):
        self.op = "select"
        return self

    def insert(self, payload):
        self.op, self.payload = "insert", payload
        return self

    def update(self, payload):
        self.op, self.payload = "update", payload
        return self

    def delete(self):
        self.op = "delete"
        return self

    def eq(self, col, val):
        self.filtros.append(lambda r: r.get(col) == val)
        return self

    def neq(self, col, val):
        self.filtros.append(lambda r: r.get(col) != val)
        return self

    def in_(self, col, vals):
        self.filtros.append(lambda r: r.get(col) in vals)
        return self

    def gte(self, col, val):
        self.filtros.append(lambda r: str(r.get(col) or "") >= val)
        return self

    def lte(self, col, val):
        self.filtros.append(lambda r: str(r.get(col) or "") <= val)
        return self

    def lt(self, col, val):
        self.filtros.append(lambda r: str(r.get(col) or "") < val)
        return self

    def order(self, *_a, **_k):
        return self

    def limit(self, n):
        self._limit = n
        return self

    def maybe_single(self):
        self.unico = "maybe"
        return self

    def single(self):
        self.unico = "single"
        return self

    # execução --------------------------------------------------------
    def _linhas(self):
        return [r for r in self.db.tabelas.setdefault(self.tabela, [])
                if all(f(r) for f in self.filtros)]

    def execute(self):
        falha = self.db.falhas.get((self.tabela, self.op))
        if falha:
            raise falha
        tabela = self.db.tabelas.setdefault(self.tabela, [])
        if self.op == "insert":
            itens = self.payload if isinstance(self.payload, list) else [self.payload]
            novos = []
            for item in itens:
                novo = {"id": str(uuid.uuid4()), "created_at": "2026-01-01T00:00:00", **copy.deepcopy(item)}
                tabela.append(novo)
                novos.append(copy.deepcopy(novo))
            return _Resp(novos)
        linhas = self._linhas()
        if self.op == "update":
            for r in linhas:
                r.update(copy.deepcopy(self.payload))
            return _Resp([copy.deepcopy(r) for r in linhas])
        if self.op == "delete":
            for r in linhas:
                tabela.remove(r)
            return _Resp([copy.deepcopy(r) for r in linhas])
        dados = [copy.deepcopy(r) for r in linhas]
        if self._limit is not None:
            dados = dados[: self._limit]
        if self.unico == "maybe":
            # supabase-py devolve None quando não há linha
            return _Resp(dados[0]) if dados else None
        if self.unico == "single":
            return _Resp(dados[0] if dados else None)
        return _Resp(dados)


class FakeAdminAuth:
    def __init__(self, db):
        self.db = db

    def create_user(self, attrs):
        if self.db.falha_create_user:
            raise self.db.falha_create_user
        email = attrs["email"].lower()
        if any(u["email"] == email for u in self.db.auth_users.values()):
            raise Exception("A user with this email address has already been registered")
        uid = str(uuid.uuid4())
        self.db.auth_users[uid] = {"id": uid, "email": email, "password": attrs["password"]}
        self.db.chamadas.append(("create_user", email))
        return SimpleNamespace(user=SimpleNamespace(id=uid, email=email))

    def delete_user(self, uid):
        self.db.chamadas.append(("delete_user", uid))
        self.db.auth_users.pop(uid, None)

    def update_user_by_id(self, uid, attrs):
        self.db.chamadas.append(("update_user_by_id", uid))
        self.db.auth_users[uid].update(attrs)

    def list_users(self, page=None, per_page=None):
        return [SimpleNamespace(id=u["id"], email=u["email"]) for u in self.db.auth_users.values()]

    def sign_out(self, token):
        pass


class FakeAuth:
    def __init__(self, db):
        self.db = db
        self.admin = FakeAdminAuth(db)

    def get_user(self, token):
        uid = self.db.tokens.get(token)
        if not uid:
            raise Exception("invalid JWT: token inválido de teste")
        u = self.db.auth_users[uid]
        return SimpleNamespace(user=SimpleNamespace(id=uid, email=u["email"]))


class FakeBucket:
    def __init__(self, db, nome):
        self.db, self.nome = db, nome

    def upload(self, path, conteudo, opcoes):
        self.db.storage[path] = {"bytes": conteudo, "opcoes": dict(opcoes), "bucket": self.nome}

    def remove(self, paths):
        for p in paths:
            self.db.storage.pop(p, None)

    def create_signed_url(self, path, ttl):
        self.db.chamadas.append(("signed_url", path, ttl))
        return {"signedURL": f"https://assinado.example/{path}?ttl={ttl}"}


class FakeStorage:
    def __init__(self, db):
        self.db = db

    def from_(self, nome):
        return FakeBucket(self.db, nome)


class FakeSupabase:
    def __init__(self):
        self.tabelas = {}
        self.auth_users = {}
        self.tokens = {}
        self.storage = {}
        self.falhas = {}
        self.falha_create_user = None
        self.chamadas = []
        self.auth = FakeAuth(self)
        self.storage_api = FakeStorage(self)

    def table(self, nome):
        return FakeQuery(self, nome)

    # util de teste --------------------------------------------------
    def criar_usuario(self, nome, papel, clinica_id, permissoes=None, ativo=True):
        uid = str(uuid.uuid4())
        email = f"{uid[:8]}@example.com"
        self.auth_users[uid] = {"id": uid, "email": email, "password": "x" * 12}
        self.tabelas.setdefault("usuarios", []).append({
            "id": uid, "nome": nome, "papel": papel, "clinica_id": clinica_id,
            "permissoes": permissoes or {}, "ativo": ativo, "percentual_repasse": 30,
            "cro": None, "created_at": "2026-01-01T00:00:00",
        })
        token = f"tok-{uid}"
        self.tokens[token] = uid
        return SimpleNamespace(id=uid, token=token, email=email)

    def linha(self, tabela, **dados):
        dados.setdefault("id", str(uuid.uuid4()))
        dados.setdefault("created_at", "2026-01-01T00:00:00")
        self.tabelas.setdefault(tabela, []).append(dados)
        return dados


# `storage` é atributo de dados no fake (dict de arquivos); as rotas chamam
# `cliente.storage.from_(...)`. Um wrapper resolve os dois usos.
class _ClienteFake:
    def __init__(self, db):
        self._db = db
        self.auth = db.auth
        self.storage = db.storage_api

    def table(self, nome):
        return self._db.table(nome)


@pytest.fixture(scope="session")
def app():
    from config import Config
    Config.RATELIMIT_ENABLED = False  # os testes fazem muitas requisições seguidas
    Config.TESTING = True
    from app import create_app
    return create_app()


@pytest.fixture
def db(app, monkeypatch):
    fake = FakeSupabase()
    cliente = _ClienteFake(fake)
    for nome, mod in list(sys.modules.items()):
        if not (nome == "app" or nome.startswith("app.")) or mod is None:
            continue
        for attr in ("supabase", "supabase_admin", "supabase_auth"):
            if hasattr(mod, attr) and not isinstance(getattr(mod, attr), type(sys)):
                monkeypatch.setattr(mod, attr, cliente)
    return fake


@pytest.fixture
def client(app):
    return app.test_client()


def auth(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def cenario(db):
    """Duas clínicas. A clínica A tem Dono, Recepção e Especialista com as
    permissões PADRÃO (nenhuma permissão extra concedida)."""
    from app.auth_utils import PERMISSOES_PADRAO

    clinica_a = str(uuid.uuid4())
    clinica_b = str(uuid.uuid4())
    dono = db.criar_usuario("Dono A", "Dono", clinica_a)
    recep = db.criar_usuario("Recepção A", "Recepção", clinica_a, dict(PERMISSOES_PADRAO["Recepção"]))
    espec = db.criar_usuario("Especialista A", "Especialista", clinica_a, dict(PERMISSOES_PADRAO["Especialista"]))
    dono_b = db.criar_usuario("Dono B", "Dono", clinica_b)
    db.linha("clinicas", id=clinica_a, dono_id=dono.id, nome_fantasia="Clínica A")
    db.linha("clinicas", id=clinica_b, dono_id=dono_b.id, nome_fantasia="Clínica B")

    paciente = db.linha("pacientes", clinica_id=clinica_a, nome="Paciente A",
                        anamnese={"alergias": "Nega"}, odontograma={"11": "carie"})
    paciente_b = db.linha("pacientes", clinica_id=clinica_b, nome="Paciente B",
                          anamnese={}, odontograma={})
    plano = db.linha("planos_tratamento", clinica_id=clinica_a, paciente_id=paciente["id"],
                     dentista_id=espec.id, titulo="Plano", status="Orcamento")
    item = db.linha("plano_itens", plano_id=plano["id"], procedimento="Resina",
                    quantidade=1, valor_unitario=100, status="Pendente", ordem=0)
    consulta = db.linha("atendimentos", clinica_id=clinica_a, paciente_id=paciente["id"],
                        dentista_id=espec.id, data_agendada="2026-01-10T10:00:00",
                        status="Agendado", evolucao_clinica="Evolução sigilosa",
                        procedimentos_descritos="Profilaxia")
    img_clinica = db.linha("paciente_imagens", clinica_id=clinica_a, paciente_id=paciente["id"],
                           nome="rx.png", storage_path=f"{clinica_a}/{paciente['id']}/rx.png", tipo="imagem")
    img_termo = db.linha("paciente_imagens", clinica_id=clinica_a, paciente_id=paciente["id"],
                         nome="termo.pdf", storage_path=f"{clinica_a}/{paciente['id']}/t.pdf",
                         tipo="termo_lgpd")
    lanc = db.linha("faturamento", clinica_id=clinica_a, paciente_id=paciente["id"],
                    valor=100, status_pagamento="Pago", dentista_responsavel=espec.id,
                    created_at=datetime.now().isoformat())

    return SimpleNamespace(
        clinica_a=clinica_a, clinica_b=clinica_b, dono=dono, recep=recep, espec=espec,
        dono_b=dono_b, paciente=paciente, paciente_b=paciente_b, plano=plano, item=item,
        consulta=consulta, img_clinica=img_clinica, img_termo=img_termo, lanc=lanc,
    )

"""RBAC — negações e dados ocultos, sobre um cenário montado UMA vez por módulo.

Cada caso confere 403 e que o banco ficou idêntico (hash de todas as tabelas).

Tudo real: contas criadas por /api/auth/registro e /api/usuarios/criar,
tokens emitidos pelo /api/auth/login, dados gravados pelas rotas no PostgreSQL.
Nenhuma permissão extra é concedida para "passar" — os membros usam
exatamente PERMISSOES_PADRAO (o que /api/usuarios/criar grava).
"""

import io
from types import SimpleNamespace

import pytest

pytestmark = [pytest.mark.rbac, pytest.mark.banco_compartilhado]

from apoio import Cenario, auth, consultar, foto_do_banco, limpar_banco

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
PDF = b"%PDF-1.7\n" + b"0" * 64


@pytest.fixture(scope="module")
def mundo(app, banco):
    """Duas clínicas, com Dono, Recepção e Especialista na A, e dados de todos os módulos."""
    limpar_banco()
    client = app.test_client()
    c = Cenario(client)
    dono = c.dono("Dono A")
    recep = c.membro(dono, "Recepção")
    espec = c.membro(dono, "Especialista")
    dono_b = c.dono("Dono B")
    h = auth(dono["token"])

    paciente = c.paciente(dono)
    assert client.put(f"/api/pacientes/{paciente['id']}", json={"odontograma": {"11": "carie"}}, headers=h).status_code == 200
    paciente_b = c.paciente(dono_b)

    plano = client.post("/api/planos/", headers=h, json={
        "paciente_id": paciente["id"], "itens": [{"procedimento": "Resina", "valor_unitario": 100}]}).get_json()
    consulta = client.post("/api/consultas/", headers=h, json={
        "paciente_id": paciente["id"], "dentista_id": espec["id"],
        "data_agendada": "2026-01-10T10:00:00", "procedimentos_descritos": "Profilaxia"}).get_json()
    assert client.put(f"/api/consultas/{consulta['id']}", headers=h,
                      json={"evolucao_clinica": "Evolução sigilosa"}).status_code == 200

    def upload(conteudo, nome, tipo):
        r = client.post("/api/imagens/upload", headers=h, content_type="multipart/form-data", data={
            "paciente_id": paciente["id"], "tipo": tipo, "file": (io.BytesIO(conteudo), nome)})
        assert r.status_code == 201, r.get_json()
        return r.get_json()

    img_clinica = upload(PNG, "rx.png", "imagem")
    img_termo = upload(PDF, "termo.pdf", "termo_lgpd")
    lanc = client.post("/api/financeiro/", headers=h, json={
        "paciente_id": paciente["id"], "valor": 100, "status_pagamento": "Pago",
        "dentista_responsavel": espec["id"]}).get_json()

    # estoque e esterilização
    forn = client.post("/api/estoque/fornecedores", headers=h, json={"nome": "Dental Sul"}).get_json()
    item = client.post("/api/estoque/itens", headers=h, json={
        "nome": "Luva", "categoria": "Material", "unidade": "cx", "estoque_minimo": 1,
        "quantidade_inicial": 5, "lote": "L1", "validade": "2030-01-01"}).get_json()
    equip = client.post("/api/esterilizacao/equipamentos", headers=h, json={"identificacao": "AUTO-01"}).get_json()

    return SimpleNamespace(
        client=client, dono=dono, recep=recep, espec=espec, dono_b=dono_b,
        paciente=paciente, paciente_b=paciente_b, plano=plano, item_plano=plano["itens"][0],
        consulta=consulta, img_clinica=img_clinica, img_termo=img_termo, lanc=lanc,
        forn=forn, item=item, equip=equip, clinica_a=dono["clinica_id"], clinica_b=dono_b["clinica_id"],
    )


# (papel, método, url, corpo) -> deve dar 403 e não alterar nada
CASOS_PROIBIDOS = [
    # ---- Recepção: sem acesso ao prontuário clínico -------------------------
    ("recep", "get", "/api/planos/?paciente_id={paciente}", None),
    ("recep", "post", "/api/planos/", {"paciente_id": "{paciente}", "itens": []}),
    ("recep", "put", "/api/planos/{plano}", {"status": "Aprovado"}),
    ("recep", "put", "/api/planos/{plano}/itens/{item_plano}", {"status": "Concluido"}),
    ("recep", "delete", "/api/planos/{plano}", None),
    ("recep", "put", "/api/pacientes/{paciente}", {"odontograma": {"11": "higido"}}),
    ("recep", "put", "/api/consultas/{consulta}", {"evolucao_clinica": "x"}),
    ("recep", "put", "/api/consultas/{consulta}", {"procedimentos_descritos": "x"}),
    ("recep", "delete", "/api/imagens/{img_clinica}", None),
    ("recep", "delete", "/api/pacientes/{paciente}", None),
    ("recep", "put", "/api/clinicas/{clinica_a}", {"nome": "Invadida"}),
    ("recep", "post", "/api/clinicas/", {"nome": "Clínica paralela"}),
    ("recep", "post", "/api/usuarios/criar", {"nome": "X", "email": "x@example.com",
                                              "senha": "senha-forte-123", "papel": "Recepção"}),
    ("recep", "patch", "/api/usuarios/{espec}/permissoes", {"permissoes": {"ver_financeiro": True}}),
    # Recepção não tem 'esterilizacao' por padrão
    ("recep", "get", "/api/esterilizacao/equipamentos", None),
    ("recep", "post", "/api/esterilizacao/equipamentos", {"identificacao": "AUTO-99"}),
    ("recep", "get", "/api/esterilizacao/ciclos", None),
    ("recep", "get", "/api/esterilizacao/pacotes", None),
    ("recep", "put", "/api/esterilizacao/equipamentos/{equip}", {"ativo": False}),
    # ---- Especialista: sem cadastro, agenda administrativa e financeiro ----
    ("espec", "post", "/api/pacientes/", {"nome": "Novo"}),
    ("espec", "put", "/api/pacientes/{paciente}", {"nome": "Outro nome"}),
    ("espec", "put", "/api/pacientes/{paciente}", {"telefone_whatsapp": "11999998888"}),
    ("espec", "delete", "/api/pacientes/{paciente}", None),
    ("espec", "get", "/api/financeiro/", None),
    ("espec", "post", "/api/financeiro/", {"paciente_id": "{paciente}", "valor": 10}),
    ("espec", "put", "/api/financeiro/{lanc}", {"valor": 1}),
    ("espec", "get", "/api/financeiro/repasses", None),
    ("espec", "post", "/api/consultas/", {"paciente_id": "{paciente}", "data_agendada": "2026-02-01T10:00:00"}),
    ("espec", "delete", "/api/consultas/{consulta}", None),
    ("espec", "put", "/api/consultas/{consulta}", {"status": "Cancelado"}),
    ("espec", "put", "/api/consultas/{consulta}", {"status": "Aguardando"}),
    ("espec", "put", "/api/consultas/{consulta}", {"data_agendada": "2026-03-01T10:00:00"}),
    ("espec", "put", "/api/clinicas/{clinica_a}", {"nome": "Invadida"}),
    ("espec", "post", "/api/clinicas/", {"nome": "Clínica paralela"}),
    ("espec", "put", "/api/usuarios/{recep}", {"nome": "X"}),
    ("espec", "put", "/api/usuarios/{recep}/senha", {"senha": "nova-senha-123"}),
    ("espec", "delete", "/api/usuarios/{recep}", None),
]


def _formatar(valor, m):
    mapa = {
        "paciente": m.paciente["id"], "plano": m.plano["id"], "item_plano": m.item_plano["id"],
        "consulta": m.consulta["id"], "img_clinica": m.img_clinica["id"],
        "lanc": m.lanc["id"], "clinica_a": m.clinica_a, "espec": m.espec["id"],
        "recep": m.recep["id"], "equip": m.equip["id"],
    }
    if isinstance(valor, str):
        return valor.format(**mapa)
    if isinstance(valor, dict):
        return {k: _formatar(v, m) for k, v in valor.items()}
    return valor


@pytest.mark.parametrize("papel,metodo,url,corpo", CASOS_PROIBIDOS,
                         ids=[f"{p}-{m}-{u}-{list((b or {}).keys())}" for p, m, u, b in CASOS_PROIBIDOS])
def test_papel_nao_acessa_funcionalidade_proibida(mundo, papel, metodo, url, corpo):
    antes = foto_do_banco()
    token = getattr(mundo, papel)["token"]
    kwargs = {"headers": auth(token)}
    if corpo is not None:
        kwargs["json"] = _formatar(corpo, mundo)
    r = getattr(mundo.client, metodo)(_formatar(url, mundo), **kwargs)
    assert r.status_code == 403, (r.status_code, r.get_json())
    assert foto_do_banco() == antes, "rota negada não pode alterar dados"


@pytest.mark.parametrize("tipo,nome,conteudo", [("imagem", "rx.png", PNG), ("laudo", "laudo.png", PNG)])
def test_recepcao_nao_envia_imagem_clinica_nem_laudo(mundo, tipo, nome, conteudo):
    antes = foto_do_banco()
    r = mundo.client.post("/api/imagens/upload", headers=auth(mundo.recep["token"]),
                          content_type="multipart/form-data", data={
                              "paciente_id": mundo.paciente["id"], "tipo": tipo,
                              "file": (io.BytesIO(conteudo), nome)})
    assert r.status_code == 403
    assert foto_do_banco() == antes


# ---- Dados clínicos ocultados de quem não tem ver_prontuario ----------------

def test_recepcao_nao_recebe_odontograma_nem_evolucao(mundo):
    c, t = mundo.client, mundo.recep["token"]
    p = c.get(f"/api/pacientes/{mundo.paciente['id']}", headers=auth(t)).get_json()
    assert "odontograma" not in p
    assert p["anamnese"]["alergias"] == "Nega"  # anamnese segue visível (coletada no cadastro)
    assert all("odontograma" not in x for x in c.get("/api/pacientes/", headers=auth(t)).get_json()["items"])
    consultas = c.get("/api/consultas/", headers=auth(t)).get_json()
    assert consultas and all("evolucao_clinica" not in x for x in consultas)
    assert consultas[0]["procedimentos_descritos"] == "Profilaxia"

    te = mundo.espec["token"]
    assert c.get(f"/api/pacientes/{mundo.paciente['id']}", headers=auth(te)).get_json()["odontograma"] == {"11": "carie"}
    assert c.get("/api/consultas/", headers=auth(te)).get_json()[0]["evolucao_clinica"] == "Evolução sigilosa"


def test_recepcao_lista_apenas_termos(mundo):
    url = f"/api/imagens/?paciente_id={mundo.paciente['id']}"
    recep = mundo.client.get(url, headers=auth(mundo.recep["token"])).get_json()
    assert [i["tipo"] for i in recep] == ["termo_lgpd"]
    espec = mundo.client.get(url, headers=auth(mundo.espec["token"])).get_json()
    assert sorted(i["tipo"] for i in espec) == ["imagem", "termo_lgpd"]


def test_metricas_financeiras_so_com_ver_financeiro(mundo):
    espec = mundo.client.get("/api/dashboard/metricas", headers=auth(mundo.espec["token"])).get_json()
    assert "receita_mes" not in espec and "pendente_mes" not in espec
    assert "consultas_hoje" in espec and espec["total_pacientes"] == 1
    dono = mundo.client.get("/api/dashboard/metricas", headers=auth(mundo.dono["token"])).get_json()
    assert dono["receita_mes"] == 100


def test_equipe_nao_expoe_permissoes_para_membros(mundo):
    membros = mundo.client.get("/api/usuarios/", headers=auth(mundo.recep["token"])).get_json()
    assert membros and all("permissoes" not in m and "percentual_repasse" not in m for m in membros)
    membros = mundo.client.get("/api/usuarios/", headers=auth(mundo.dono["token"])).get_json()
    assert all("permissoes" in m for m in membros)


def test_membros_criados_recebem_as_permissoes_padrao(mundo):
    from app.auth_utils import PERMISSOES_PADRAO
    for m, papel in ((mundo.recep, "Recepção"), (mundo.espec, "Especialista")):
        (perm,), = consultar("SELECT permissoes FROM usuarios WHERE id = %s", [m["id"]])
        assert perm == PERMISSOES_PADRAO[papel]


@pytest.mark.parametrize("url", [
    "/api/pacientes/", "/api/consultas/", "/api/financeiro/", "/api/planos/?paciente_id=x",
    "/api/imagens/?paciente_id=x", "/api/usuarios/", "/api/clinicas/", "/api/dashboard/metricas",
    "/api/estoque/itens", "/api/estoque/fornecedores", "/api/estoque/movimentacoes", "/api/estoque/resumo",
    "/api/esterilizacao/equipamentos", "/api/esterilizacao/ciclos", "/api/esterilizacao/pacotes",
])
def test_sem_token_ou_token_falso_retorna_401(mundo, url):
    assert mundo.client.get(url).status_code == 401
    assert mundo.client.get(url, headers=auth("token-falso")).status_code == 401

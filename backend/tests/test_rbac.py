"""RBAC no backend: cada papel, com as permissões PADRÃO, só acessa o que pode.

Nenhum teste concede permissão extra para "passar": o cenário usa exatamente
PERMISSOES_PADRAO. Os testes de override individual verificam que o RBAC
respeita o que o Dono configurou — nos dois sentidos.
"""

import io

import pytest

from conftest import auth

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


def _req(client, metodo, url, token, corpo=None, arquivo=None):
    kwargs = {"headers": auth(token)}
    if arquivo is not None:
        kwargs["data"] = arquivo
        kwargs["content_type"] = "multipart/form-data"
    elif corpo is not None:
        kwargs["json"] = corpo
    return getattr(client, metodo)(url, **kwargs)


# (papel, método, url, corpo) -> deve dar 403
CASOS_PROIBIDOS = [
    # ---- Recepção: sem acesso ao prontuário clínico -------------------------
    ("recep", "get", "/api/planos/?paciente_id={paciente}", None),
    ("recep", "post", "/api/planos/", {"paciente_id": "{paciente}", "itens": []}),
    ("recep", "put", "/api/planos/{plano}", {"status": "Aprovado"}),
    ("recep", "put", "/api/planos/{plano}/itens/{item}", {"status": "Concluido"}),
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


def _formatar(valor, c):
    mapa = {
        "paciente": c.paciente["id"], "plano": c.plano["id"], "item": c.item["id"],
        "consulta": c.consulta["id"], "img_clinica": c.img_clinica["id"],
        "img_termo": c.img_termo["id"], "lanc": c.lanc["id"], "clinica_a": c.clinica_a,
        "espec": c.espec.id, "recep": c.recep.id,
    }
    if isinstance(valor, str):
        return valor.format(**mapa)
    if isinstance(valor, dict):
        return {k: _formatar(v, c) for k, v in valor.items()}
    return valor


@pytest.mark.parametrize("papel,metodo,url,corpo", CASOS_PROIBIDOS,
                         ids=[f"{p}-{m}-{u}-{list((b or {}).keys())}" for p, m, u, b in CASOS_PROIBIDOS])
def test_papel_nao_acessa_funcionalidade_proibida(client, cenario, db, papel, metodo, url, corpo):
    antes = repr(db.tabelas)
    r = _req(client, metodo, _formatar(url, cenario), getattr(cenario, papel).token, _formatar(corpo, cenario))
    assert r.status_code == 403, (r.status_code, r.get_json())
    assert repr(db.tabelas) == antes, "rota negada não pode alterar dados"


def test_recepcao_nao_envia_imagem_clinica(client, cenario, db):
    r = _req(client, "post", "/api/imagens/upload", cenario.recep.token, arquivo={
        "paciente_id": cenario.paciente["id"], "tipo": "imagem",
        "file": (io.BytesIO(PNG), "rx.png"),
    })
    assert r.status_code == 403
    assert db.storage == {}


def test_recepcao_nao_envia_laudo(client, cenario, db):
    r = _req(client, "post", "/api/imagens/upload", cenario.recep.token, arquivo={
        "paciente_id": cenario.paciente["id"], "tipo": "laudo",
        "file": (io.BytesIO(PNG), "laudo.png"),
    })
    assert r.status_code == 403


# ---- O que cada papel PODE fazer (o RBAC não pode quebrar o fluxo atual) ----

def test_recepcao_fluxos_permitidos(client, cenario):
    t = cenario.recep.token
    assert _req(client, "get", "/api/pacientes/", t).status_code == 200
    assert _req(client, "get", f"/api/pacientes/{cenario.paciente['id']}", t).status_code == 200
    # Edita cadastro + anamnese (tela RegisterPatient)
    r = _req(client, "put", f"/api/pacientes/{cenario.paciente['id']}", t,
             {"rg": "123", "anamnese": {"alergias": "Dipirona"}})
    assert r.status_code == 200, r.get_json()
    # Agenda: check-in, falta, cancelamento
    for status in ("Aguardando", "Faltou", "Cancelado"):
        r = _req(client, "put", f"/api/consultas/{cenario.consulta['id']}", t, {"status": status})
        assert r.status_code == 200, (status, r.get_json())
    assert _req(client, "get", "/api/financeiro/", t).status_code == 200
    # Termos de consentimento continuam sendo arquivados pela recepção
    r = _req(client, "post", "/api/imagens/upload", t, arquivo={
        "paciente_id": cenario.paciente["id"], "tipo": "termo_consentimento",
        "file": (io.BytesIO(b"%PDF-1.7\n..."), "termo.pdf"),
    })
    assert r.status_code == 201, r.get_json()


def test_especialista_fluxos_permitidos(client, cenario):
    t = cenario.espec.token
    pid = cenario.paciente["id"]
    assert _req(client, "get", f"/api/planos/?paciente_id={pid}", t).status_code == 200
    assert _req(client, "put", f"/api/pacientes/{pid}", t, {"odontograma": {"11": "restaurado"}}).status_code == 200
    assert _req(client, "put", f"/api/pacientes/{pid}", t, {"anamnese": {"alergias": "Nega"}}).status_code == 200
    r = _req(client, "post", "/api/planos/", t, {"paciente_id": pid, "itens": [{"procedimento": "X", "valor_unitario": 10}]})
    assert r.status_code == 201, r.get_json()
    r = _req(client, "put", f"/api/planos/{cenario.plano['id']}/itens/{cenario.item['id']}", t, {"status": "Concluido"})
    assert r.status_code == 200
    # Encerramento do atendimento (PainelEspecialista)
    r = _req(client, "put", f"/api/consultas/{cenario.consulta['id']}", t, {
        "procedimentos_descritos": "Resina", "evolucao_clinica": "Ok", "status": "Finalizado",
    })
    assert r.status_code == 200, r.get_json()
    r = _req(client, "post", "/api/imagens/upload", t, arquivo={
        "paciente_id": pid, "tipo": "imagem", "file": (io.BytesIO(PNG), "rx.png"),
    })
    assert r.status_code == 201
    assert _req(client, "get", "/api/dashboard/metricas", t).status_code == 200


def test_dono_tem_acesso_total_na_propria_clinica(client, cenario):
    t = cenario.dono.token
    pid = cenario.paciente["id"]
    assert _req(client, "get", f"/api/planos/?paciente_id={pid}", t).status_code == 200
    assert _req(client, "get", "/api/financeiro/repasses", t).status_code == 200
    assert _req(client, "put", f"/api/clinicas/{cenario.clinica_a}", t, {"nome": "Clínica A+"}).status_code == 200
    assert _req(client, "delete", f"/api/imagens/{cenario.img_clinica['id']}", t).status_code == 200
    assert _req(client, "delete", f"/api/pacientes/{pid}", t).status_code == 200


# ---- Dados clínicos ocultados de quem não tem ver_prontuario ----------------

def test_recepcao_nao_recebe_odontograma(client, cenario):
    r = _req(client, "get", f"/api/pacientes/{cenario.paciente['id']}", cenario.recep.token)
    assert r.status_code == 200
    assert "odontograma" not in r.get_json()
    assert r.get_json()["anamnese"] == {"alergias": "Nega"}  # anamnese segue visível (coletada no cadastro)
    lista = _req(client, "get", "/api/pacientes/", cenario.recep.token).get_json()
    assert all("odontograma" not in p for p in lista)


def test_especialista_recebe_odontograma(client, cenario):
    r = _req(client, "get", f"/api/pacientes/{cenario.paciente['id']}", cenario.espec.token)
    assert r.get_json()["odontograma"] == {"11": "carie"}


def test_recepcao_nao_recebe_evolucao_clinica(client, cenario):
    dados = _req(client, "get", "/api/consultas/", cenario.recep.token).get_json()
    assert dados and all("evolucao_clinica" not in c for c in dados)
    assert dados[0]["procedimentos_descritos"] == "Profilaxia"
    dados = _req(client, "get", "/api/consultas/", cenario.espec.token).get_json()
    assert dados[0]["evolucao_clinica"] == "Evolução sigilosa"


def test_recepcao_lista_apenas_termos(client, cenario):
    dados = _req(client, "get", f"/api/imagens/?paciente_id={cenario.paciente['id']}", cenario.recep.token).get_json()
    assert [i["tipo"] for i in dados] == ["termo_lgpd"]
    dados = _req(client, "get", f"/api/imagens/?paciente_id={cenario.paciente['id']}", cenario.espec.token).get_json()
    assert sorted(i["tipo"] for i in dados) == ["imagem", "termo_lgpd"]


def test_metricas_financeiras_so_com_ver_financeiro(client, cenario):
    espec = _req(client, "get", "/api/dashboard/metricas", cenario.espec.token).get_json()
    assert "receita_mes" not in espec and "pendente_mes" not in espec
    assert "consultas_hoje" in espec and "total_pacientes" in espec
    dono = _req(client, "get", "/api/dashboard/metricas", cenario.dono.token).get_json()
    assert dono["receita_mes"] == 100


def test_equipe_nao_expoe_permissoes_para_membros(client, cenario):
    membros = _req(client, "get", "/api/usuarios/", cenario.recep.token).get_json()
    assert membros and all("permissoes" not in m and "percentual_repasse" not in m for m in membros)
    membros = _req(client, "get", "/api/usuarios/", cenario.dono.token).get_json()
    assert all("permissoes" in m for m in membros)


# ---- Permissões individuais configuradas pelo Dono --------------------------

def _definir_permissoes(db, usuario_id, permissoes):
    for u in db.tabelas["usuarios"]:
        if u["id"] == usuario_id:
            u["permissoes"] = permissoes


def test_permissao_revogada_pelo_dono_e_respeitada(client, cenario, db):
    from app.auth_utils import PERMISSOES_PADRAO
    _definir_permissoes(db, cenario.espec.id, {**PERMISSOES_PADRAO["Especialista"], "ver_prontuario": False})
    r = _req(client, "get", f"/api/planos/?paciente_id={cenario.paciente['id']}", cenario.espec.token)
    assert r.status_code == 403


def test_perfil_sem_permissoes_cai_no_padrao_do_papel(client, cenario, db):
    _definir_permissoes(db, cenario.recep.id, {})
    r = _req(client, "get", f"/api/planos/?paciente_id={cenario.paciente['id']}", cenario.recep.token)
    assert r.status_code == 403
    assert _req(client, "get", "/api/pacientes/", cenario.recep.token).status_code == 200


def test_usuario_desativado_e_bloqueado_mesmo_com_token_valido(client, cenario, db):
    for u in db.tabelas["usuarios"]:
        if u["id"] == cenario.recep.id:
            u["ativo"] = False
    r = _req(client, "get", "/api/pacientes/", cenario.recep.token)
    assert r.status_code == 403


@pytest.mark.parametrize("url", [
    "/api/pacientes/", "/api/consultas/", "/api/financeiro/", "/api/planos/?paciente_id=x",
    "/api/imagens/?paciente_id=x", "/api/usuarios/", "/api/clinicas/", "/api/dashboard/metricas",
])
def test_sem_token_retorna_401(client, db, url):
    assert client.get(url).status_code == 401
    assert client.get(url, headers=auth("token-falso")).status_code == 401


# ---- Isolamento por clínica (pertence_a_clinica / filtros por clinica_id) ----

def test_isolamento_entre_clinicas(client, cenario, db):
    t = cenario.dono.token
    pb = cenario.paciente_b["id"]
    assert _req(client, "get", f"/api/pacientes/{pb}", t).status_code == 404
    assert _req(client, "put", f"/api/pacientes/{pb}", t, {"nome": "X"}).status_code == 404
    assert _req(client, "delete", f"/api/pacientes/{pb}", t).status_code == 404
    assert _req(client, "post", "/api/planos/", t, {"paciente_id": pb}).status_code == 404
    assert _req(client, "post", "/api/consultas/", t, {"paciente_id": pb, "data_agendada": "2026-02-01T10:00"}).status_code == 404
    assert _req(client, "post", "/api/financeiro/", t, {"paciente_id": pb, "valor": 10}).status_code == 404
    assert _req(client, "put", f"/api/clinicas/{cenario.clinica_b}", t, {"nome": "X"}).status_code == 403
    assert _req(client, "get", f"/api/clinicas/{cenario.clinica_b}", t).status_code == 403
    assert _req(client, "get", f"/api/dashboard/metricas?clinica_id={cenario.clinica_b}", t).status_code == 403
    r = _req(client, "post", "/api/imagens/upload", t, arquivo={
        "paciente_id": pb, "tipo": "imagem", "file": (io.BytesIO(PNG), "rx.png"),
    })
    assert r.status_code == 403
    assert db.storage == {}
    # Dono B não enxerga nada da clínica A
    assert _req(client, "get", f"/api/pacientes/{cenario.paciente['id']}", cenario.dono_b.token).status_code == 404
    assert _req(client, "get", f"/api/imagens/?paciente_id={cenario.paciente['id']}", cenario.dono_b.token).get_json() == []
    assert _req(client, "delete", f"/api/imagens/{cenario.img_clinica['id']}", cenario.dono_b.token).status_code == 404

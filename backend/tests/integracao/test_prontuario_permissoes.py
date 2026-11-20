"""Matriz de permissões de pacientes e prontuário (papel × ação), com as
permissões PADRÃO de cada papel, sobre um cenário real montado uma vez.

Ações que só leem ou que devem ser negadas rodam aqui (o banco é conferido
por hash para provar que nada mudou). Ações permitidas que gravam estão em
test_prontuario_escritas (banco limpo por teste).

Matriz vigente (PERMISSOES_PADRAO + regras por campo das rotas):
| Ação                               | Dono | Especialista | Recepção |
|------------------------------------|------|--------------|----------|
| listar/ver paciente (cadastro)     | sim  | sim          | sim      |
| ver anamnese                       | sim  | sim          | sim (coletada no cadastro) |
| ver odontograma                    | sim  | sim          | não (campo omitido) |
| cadastrar / editar dados cadastrais| sim  | não (403)    | sim      |
| editar anamnese                    | sim  | sim          | sim      |
| editar odontograma                 | sim  | sim          | não (403)|
| excluir paciente                   | sim  | não (403)    | não (403)|
| ver planos de tratamento           | sim  | sim          | não (403)|
| criar/alterar planos               | sim  | sim          | não (403)|
| ver evolução clínica               | sim  | sim          | não (campo omitido) |
| registrar evolução/procedimentos   | sim  | sim          | não (403)|
| ver agenda                         | sim  | sim          | sim      |
"""

from types import SimpleNamespace

import pytest

from apoio import Cenario, auth, foto_do_banco, limpar_banco

pytestmark = [pytest.mark.prontuario, pytest.mark.rbac, pytest.mark.banco_compartilhado]

UUID_INEXISTENTE = "00000000-0000-4000-8000-000000000000"


@pytest.fixture(scope="module")
def m(app, banco):
    limpar_banco()
    client = app.test_client()
    c = Cenario(client)
    dono = c.dono("Dono A")
    recep, espec = c.membro(dono, "Recepção"), c.membro(dono, "Especialista")
    dono_b = c.dono("Dono B")
    h = auth(dono["token"])
    pac = c.paciente(dono, anamnese={"alergias": "Penicilina", "medicacoes": "Nenhuma", "condicoes": "Nenhuma"})
    client.put(f"/api/pacientes/{pac['id']}", headers=h, json={"odontograma": {"36": "carie"}})
    plano = client.post("/api/planos/", headers=h, json={
        "paciente_id": pac["id"], "itens": [{"procedimento": "Resina", "dente": "36", "valor_unitario": 150}]}).get_json()
    consulta = client.post("/api/consultas/", headers=h, json={
        "paciente_id": pac["id"], "dentista_id": espec["id"], "data_agendada": "2026-11-10T09:00:00"}).get_json()
    client.put(f"/api/consultas/{consulta['id']}", headers=h, json={"evolucao_clinica": "Cárie profunda no 36"})
    return SimpleNamespace(client=client, dono=dono, recep=recep, espec=espec, dono_b=dono_b,
                           pac=pac, plano=plano, consulta=consulta)


def _req(m, papel, metodo, url, corpo=None):
    kwargs = {"headers": auth(getattr(m, papel)["token"])}
    if corpo is not None:
        kwargs["json"] = corpo
    return getattr(m.client, metodo)(url.format(p=m.pac["id"], plano=m.plano["id"], c=m.consulta["id"]), **kwargs)


LEITURAS = [
    # (ação, método, url, {papel: status})
    ("listar pacientes", "get", "/api/pacientes/", {"dono": 200, "espec": 200, "recep": 200}),
    ("ver paciente", "get", "/api/pacientes/{p}", {"dono": 200, "espec": 200, "recep": 200}),
    ("ver planos", "get", "/api/planos/?paciente_id={p}", {"dono": 200, "espec": 200, "recep": 403}),
    ("ver agenda/histórico", "get", "/api/consultas/?paciente_id={p}", {"dono": 200, "espec": 200, "recep": 200}),
    ("ver documentos", "get", "/api/imagens/?paciente_id={p}", {"dono": 200, "espec": 200, "recep": 200}),
]
NEGADAS = [
    ("especialista cadastra paciente", "espec", "post", "/api/pacientes/", {"nome": "X"}),
    ("especialista edita cadastro", "espec", "put", "/api/pacientes/{p}", {"nome": "Outro"}),
    ("especialista edita cadastro junto da anamnese", "espec", "put", "/api/pacientes/{p}",
     {"anamnese": {"alergias": "Nega"}, "telefone_whatsapp": "11999990000"}),
    ("especialista exclui paciente", "espec", "delete", "/api/pacientes/{p}", None),
    ("recepção exclui paciente", "recep", "delete", "/api/pacientes/{p}", None),
    ("recepção edita odontograma", "recep", "put", "/api/pacientes/{p}", {"odontograma": {"11": "x"}}),
    ("recepção edita odontograma junto do cadastro", "recep", "put", "/api/pacientes/{p}",
     {"nome": "Y", "odontograma": {"11": "x"}}),
    ("recepção cria plano", "recep", "post", "/api/planos/", {"paciente_id": "{p}", "itens": []}),
    ("recepção altera plano", "recep", "put", "/api/planos/{plano}", {"status": "Aprovado"}),
    ("recepção exclui plano", "recep", "delete", "/api/planos/{plano}", None),
    ("recepção registra evolução", "recep", "put", "/api/consultas/{c}", {"evolucao_clinica": "x"}),
    ("recepção registra procedimentos", "recep", "put", "/api/consultas/{c}", {"procedimentos_descritos": "x"}),
    ("especialista remarca (agenda é da recepção)", "espec", "put", "/api/consultas/{c}",
     {"data_agendada": "2026-11-10T15:00:00"}),
    ("especialista troca profissional", "espec", "put", "/api/consultas/{c}", {"dentista_id": "{p}"}),
]


@pytest.mark.parametrize("acao,metodo,url,esperado", LEITURAS, ids=[x[0] for x in LEITURAS])
@pytest.mark.parametrize("papel", ["dono", "espec", "recep"])
def test_leituras_por_papel(m, acao, metodo, url, esperado, papel):
    antes = foto_do_banco()
    assert _req(m, papel, metodo, url).status_code == esperado[papel]
    assert foto_do_banco() == antes


@pytest.mark.parametrize("acao,papel,metodo,url,corpo", NEGADAS, ids=[x[0] for x in NEGADAS])
def test_acoes_sem_permissao_dao_403_e_nao_alteram(m, acao, papel, metodo, url, corpo):
    antes = foto_do_banco()
    if isinstance(corpo, dict):
        corpo = {k: (v.format(p=m.pac["id"]) if isinstance(v, str) else v) for k, v in corpo.items()}
    r = _req(m, papel, metodo, url, corpo)
    assert r.status_code == 403, (r.status_code, r.get_json())
    assert foto_do_banco() == antes


def test_recepcao_ve_so_o_necessario(m):
    paciente = _req(m, "recep", "get", "/api/pacientes/{p}").get_json()
    assert paciente["anamnese"]["alergias"] == "Penicilina"
    assert "odontograma" not in paciente
    assert all("odontograma" not in p for p in _req(m, "recep", "get", "/api/pacientes/").get_json())
    historico = _req(m, "recep", "get", "/api/consultas/?paciente_id={p}").get_json()
    assert historico and all("evolucao_clinica" not in c for c in historico)


def test_profissional_ve_o_prontuario(m):
    for papel in ("espec", "dono"):
        assert _req(m, papel, "get", "/api/pacientes/{p}").get_json()["odontograma"] == {"36": "carie"}
        historico = _req(m, papel, "get", "/api/consultas/?paciente_id={p}").get_json()
        assert historico[0]["evolucao_clinica"] == "Cárie profunda no 36"
        planos = _req(m, papel, "get", "/api/planos/?paciente_id={p}").get_json()
        assert planos[0]["itens"][0]["dente"] == "36"


ROTAS_DO_PACIENTE = [
    ("get", "/api/pacientes/{x}", None),
    ("put", "/api/pacientes/{x}", {"nome": "Invasor"}),
    ("put", "/api/pacientes/{x}", {"anamnese": {"alergias": "x"}}),
    ("put", "/api/pacientes/{x}", {"odontograma": {"11": "x"}}),
    ("delete", "/api/pacientes/{x}", None),
]


@pytest.mark.isolamento
@pytest.mark.parametrize("metodo,url,corpo", ROTAS_DO_PACIENTE, ids=[f"{a} {c}" for a, b, c in ROTAS_DO_PACIENTE])
def test_paciente_de_outra_clinica_e_invisivel(m, metodo, url, corpo):
    antes = foto_do_banco()
    r = getattr(m.client, metodo)(url.format(x=m.pac["id"]), headers=auth(m.dono_b["token"]),
                                  **({"json": corpo} if corpo else {}))
    assert r.status_code == 404, r.get_json()
    assert foto_do_banco() == antes


@pytest.mark.isolamento
def test_dados_clinicos_de_outra_clinica_por_parametro(m):
    h = auth(m.dono_b["token"])
    pid = m.pac["id"]
    assert m.client.get(f"/api/planos/?paciente_id={pid}", headers=h).get_json() == []
    assert m.client.get(f"/api/consultas/?paciente_id={pid}", headers=h).get_json() == []
    assert m.client.get(f"/api/imagens/?paciente_id={pid}", headers=h).get_json() == []
    assert m.client.put(f"/api/planos/{m.plano['id']}", headers=h, json={"status": "Aprovado"}).status_code == 404
    assert m.client.put(f"/api/consultas/{m.consulta['id']}", headers=h, json={"evolucao_clinica": "x"}).status_code == 404
    assert m.client.delete(f"/api/consultas/{m.consulta['id']}", headers=h).status_code == 404


@pytest.mark.parametrize("url,metodo", [
    ("/api/pacientes/abc", "get"), ("/api/pacientes/1%20OR%201=1", "get"),
    ("/api/pacientes/abc", "put"), ("/api/pacientes/abc", "delete"),
    ("/api/planos/?paciente_id=abc", "get"), ("/api/consultas/?paciente_id=abc", "get"),
    ("/api/consultas/abc", "put"), ("/api/consultas/abc", "delete"), ("/api/planos/abc", "delete"),
    ("/api/imagens/?paciente_id=abc", "get"), ("/api/imagens/abc/download", "get"),
])
def test_ids_manipulados_dao_400_sem_detalhes(m, url, metodo):
    r = getattr(m.client, metodo)(url, headers=auth(m.dono["token"]), json={"nome": "x", "evolucao_clinica": "x"})
    assert r.status_code == 400, r.get_json()
    assert r.get_json() == {"error": "Identificador inválido."}


@pytest.mark.parametrize("url,metodo", [
    (f"/api/pacientes/{UUID_INEXISTENTE}", "get"), (f"/api/pacientes/{UUID_INEXISTENTE}", "put"),
    (f"/api/consultas/{UUID_INEXISTENTE}", "put"), (f"/api/imagens/{UUID_INEXISTENTE}/download", "get"),
])
def test_ids_inexistentes_dao_404(m, url, metodo):
    r = getattr(m.client, metodo)(url, headers=auth(m.dono["token"]), json={"nome": "x", "evolucao_clinica": "x"})
    assert r.status_code == 404


def test_sem_autenticacao(m):
    for url in ("/api/pacientes/", f"/api/pacientes/{m.pac['id']}", f"/api/planos/?paciente_id={m.pac['id']}",
                "/api/consultas/"):
        assert m.client.get(url).status_code == 401
        assert m.client.get(url, headers=auth("token.adulterado.x")).status_code == 401

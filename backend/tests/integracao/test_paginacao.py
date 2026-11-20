"""Paginação das listagens (?page=&per_page=) e busca de pacientes no banco.

Cenário montado uma vez (banco_compartilhado): a clínica A tem 45 pacientes,
atendimentos e lançamentos; a clínica B não tem nenhum. Os testes só leem.
"""

from types import SimpleNamespace

import pytest

from apoio import Cenario, auth, executar, gerar_cpf, limpar_banco

pytestmark = [pytest.mark.rotas, pytest.mark.isolamento, pytest.mark.banco_compartilhado]

TOTAL_PACIENTES = 45


@pytest.fixture(scope="module")
def m(app, banco):
    limpar_banco()
    client = app.test_client()
    c = Cenario(client)
    dono, dono_b = c.dono("Dono A"), c.dono("Dono B")
    espec = c.membro(dono, "Especialista")
    h = auth(dono["token"])

    # 1 paciente pela API (fluxo real) + 44 direto no banco (rápido), com
    # created_at distintos para a ordem ser determinística.
    marcos = c.paciente(dono, nome="Marcos Pereira", cpf=gerar_cpf(987654321),
                        telefone_whatsapp="62988887777")
    executar(
        """
        INSERT INTO pacientes (clinica_id, nome, cpf, telefone_whatsapp, created_at)
        SELECT %s, 'Paciente ' || lpad(g::text, 2, '0'), lpad(g::text, 11, '0'), '6290000' || lpad(g::text, 4, '0'),
               NOW() - (g || ' minutes')::interval
        FROM generate_series(1, %s) g
        """,
        [dono["clinica_id"], TOTAL_PACIENTES - 1],
    )

    consultas = []
    for dia, hora in (("2026-03-10", "09:00"), ("2026-03-11", "09:00"), ("2026-03-11", "10:00"), ("2026-03-20", "09:00")):
        r = client.post("/api/consultas/", headers=h, json={
            "paciente_id": marcos["id"], "dentista_id": espec["id"], "data_agendada": f"{dia}T{hora}:00"})
        assert r.status_code == 201, r.get_json()
        consultas.append(r.get_json())

    for valor, status in ((100, "Pago"), (50, "Pendente"), (30, "Pago")):
        r = client.post("/api/financeiro/", headers=h, json={
            "paciente_id": marcos["id"], "valor": valor, "status_pagamento": status, "forma_pagamento": "Pix"})
        assert r.status_code == 201, r.get_json()

    return SimpleNamespace(client=client, dono=dono, dono_b=dono_b, marcos=marcos, h=h, consultas=consultas)


def _get(m, url, quem=None):
    r = m.client.get(url, headers=auth((quem or m.dono)["token"]))
    return r.status_code, r.get_json()


# ---- contrato da paginação ------------------------------------------------

def test_padrao_e_20_por_pagina_com_total(m):
    status, d = _get(m, "/api/pacientes/")
    assert status == 200
    assert set(d) == {"items", "page", "per_page", "total"}
    assert (d["page"], d["per_page"], d["total"]) == (1, 20, TOTAL_PACIENTES)
    assert len(d["items"]) == 20


@pytest.mark.parametrize("pedido, efetivo", [("5", 20), ("20", 20), ("35", 35), ("50", 50), ("500", 50), ("-3", 20)])
def test_per_page_fica_entre_20_e_50(m, pedido, efetivo):
    _, d = _get(m, f"/api/pacientes/?per_page={pedido}")
    assert d["per_page"] == efetivo
    assert len(d["items"]) == min(efetivo, TOTAL_PACIENTES)


def test_ultima_pagina_parcial_e_paginas_sem_repeticao(m):
    paginas = [_get(m, f"/api/pacientes/?page={n}")[1] for n in (1, 2, 3)]
    assert [len(p["items"]) for p in paginas] == [20, 20, 5]
    ids = [x["id"] for p in paginas for x in p["items"]]
    assert len(ids) == len(set(ids)) == TOTAL_PACIENTES
    assert all(p["total"] == TOTAL_PACIENTES for p in paginas)


def test_pagina_alem_do_fim_vem_vazia_com_total(m):
    status, d = _get(m, "/api/pacientes/?page=99")
    assert status == 200
    assert d["items"] == [] and d["total"] == TOTAL_PACIENTES and d["page"] == 99


def test_pagina_menor_que_1_vira_1(m):
    _, d = _get(m, "/api/pacientes/?page=0")
    assert d["page"] == 1 and len(d["items"]) == 20


@pytest.mark.parametrize("qs", ["page=abc", "per_page=muitos", "page=1.5"])
def test_parametro_nao_numerico_e_400(m, qs):
    status, d = _get(m, f"/api/pacientes/?{qs}")
    assert status == 400 and "page" in d["error"]


def test_ordem_mais_recentes_primeiro(m):
    _, d = _get(m, "/api/pacientes/?per_page=50")
    assert d["items"][0]["id"] == m.marcos["id"]  # criado por último
    assert d["items"][1]["nome"] == "Paciente 01"


# ---- busca no banco -------------------------------------------------------

def test_busca_por_nome_sem_diferenciar_maiusculas(m):
    _, d = _get(m, "/api/pacientes/?busca=marcos")
    assert d["total"] == 1 and d["items"][0]["id"] == m.marcos["id"]


def test_busca_por_cpf_com_pontuacao(m):
    cpf = m.marcos["cpf"]
    formatado = f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"
    _, d = _get(m, f"/api/pacientes/?busca={formatado}")
    assert [p["id"] for p in d["items"]] == [m.marcos["id"]]


def test_busca_por_telefone(m):
    _, d = _get(m, "/api/pacientes/?busca=88887777")
    assert [p["id"] for p in d["items"]] == [m.marcos["id"]]


def test_busca_paginada(m):
    _, d = _get(m, "/api/pacientes/?busca=Paciente&page=3")
    assert d["total"] == TOTAL_PACIENTES - 1 and len(d["items"]) == 4


@pytest.mark.parametrize("termo", ["a,b", "x)or(1=1", "%", "*", "nome.eq.x", "\"'"])
def test_busca_com_caracteres_especiais_nao_quebra_nem_injeta(m, termo):
    from urllib.parse import quote
    status, d = _get(m, f"/api/pacientes/?busca={quote(termo)}")
    assert status == 200
    assert d["total"] <= TOTAL_PACIENTES


def test_lista_traz_ultima_consulta_calculada_no_servidor(m):
    _, d = _get(m, "/api/pacientes/?busca=Marcos")
    assert d["items"][0]["ultima_consulta"] == "2026-03-20T09:00:00"
    _, outros = _get(m, "/api/pacientes/?busca=Paciente 01")
    assert outros["items"][0]["ultima_consulta"] is None


def test_outra_clinica_nao_ve_nada(m):
    _, d = _get(m, "/api/pacientes/?per_page=50", m.dono_b)
    assert d["items"] == [] and d["total"] == 0
    _, d = _get(m, "/api/pacientes/?busca=Marcos", m.dono_b)
    assert d["total"] == 0
    _, opcoes = _get(m, "/api/pacientes/opcoes", m.dono_b)
    assert opcoes == []


# ---- lista curta para campos de seleção -------------------------------------

def test_opcoes_com_busca_limita_a_20(m):
    _, lista = _get(m, "/api/pacientes/opcoes?busca=Paciente")
    assert len(lista) == 20
    assert set(lista[0]) == {"id", "nome", "cpf", "telefone_whatsapp"}


def test_opcoes_sem_busca_traz_todos_por_nome(m):
    _, lista = _get(m, "/api/pacientes/opcoes")
    assert len(lista) == TOTAL_PACIENTES
    nomes = [p["nome"] for p in lista]
    assert nomes == sorted(nomes)


# ---- agenda / financeiro / estoque ------------------------------------------

def test_agenda_filtra_periodo_no_banco(m):
    _, dia = _get(m, "/api/consultas/?data_inicio=2026-03-11&data_fim=2026-03-11")
    assert [c["data_agendada"] for c in dia] == ["2026-03-11T09:00:00", "2026-03-11T10:00:00"]
    _, semana = _get(m, "/api/consultas/?data_inicio=2026-03-09&data_fim=2026-03-15")
    assert len(semana) == 3
    _, so_inicio = _get(m, "/api/consultas/?data_inicio=2026-03-20")
    assert len(so_inicio) == 1


@pytest.mark.parametrize("qs", ["data_inicio=11/03/2026", "data_inicio=2026-03-12&data_fim=2026-03-10",
                                "data_inicio=2020-01-01&data_fim=2026-01-01"])
def test_agenda_periodo_invalido_e_400(m, qs):
    status, _ = _get(m, f"/api/consultas/?{qs}")
    assert status == 400


def test_agenda_paginada_quando_pedido(m):
    _, d = _get(m, "/api/consultas/?page=1&per_page=20")
    assert d["total"] == 4 and len(d["items"]) == 4 and d["per_page"] == 20
    _, sem_page = _get(m, "/api/consultas/")
    assert isinstance(sem_page, list) and len(sem_page) == 4


def test_financeiro_paginado_e_filtrado(m):
    _, d = _get(m, "/api/financeiro/?page=1")
    assert d["total"] == 3 and d["per_page"] == 20
    _, pagos = _get(m, "/api/financeiro/?page=1&status_pagamento=Pago")
    assert pagos["total"] == 2
    _, do_paciente = _get(m, f"/api/financeiro/?paciente_id={m.marcos['id']}")
    assert len(do_paciente) == 3


def test_financeiro_resumo_somado_no_servidor(m):
    _, r = _get(m, "/api/financeiro/resumo")
    assert r["total_lancamentos"] == 3
    assert r["pago_mes"] == 130 and r["pendente_mes"] == 50
    assert len(r["receita_mensal"]) == 6 and r["receita_mensal"][-1]["pago"] == 130
    assert r["por_forma"] == [{"forma": "Pix", "valor": 130}]
    _, vazio = _get(m, "/api/financeiro/resumo", m.dono_b)
    assert vazio["total_lancamentos"] == 0 and vazio["pago_mes"] == 0


def test_estoque_itens_paginados(m):
    for n in range(23):
        r = m.client.post("/api/estoque/itens", headers=m.h, json={
            "nome": f"Item {n:02d}", "categoria": "Material", "unidade": "un",
            "estoque_minimo": 1, "quantidade_inicial": 2})
        assert r.status_code == 201, r.get_json()
    _, p2 = _get(m, "/api/estoque/itens?page=2")
    assert p2["total"] == 23 and len(p2["items"]) == 3
    assert all(i["quantidade_atual"] == 2 for i in p2["items"])
    _, mov = _get(m, "/api/estoque/movimentacoes?page=1&per_page=20")
    assert mov["total"] == 23 and len(mov["items"]) == 20
    _, legado = _get(m, "/api/estoque/itens")
    assert isinstance(legado, list) and len(legado) == 23

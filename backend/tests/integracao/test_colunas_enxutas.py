"""Consultas enxutas: as listagens devolvem só as colunas que as telas exibem.

O detalhe (GET /<id>) continua trazendo o registro completo — é a tela que
mostra/edita tudo.
"""

import pytest

from apoio import auth

pytestmark = pytest.mark.rotas


@pytest.fixture
def base(client, cenario):
    dono = cenario.dono("Dono")
    espec = cenario.membro(dono, "Especialista")
    recep = cenario.membro(dono, "Recepção")
    pac = cenario.paciente(dono)
    h = auth(dono["token"])
    r = client.post("/api/consultas/", headers=h, json={
        "paciente_id": pac["id"], "dentista_id": espec["id"], "data_agendada": "2026-05-04T10:00:00"})
    assert r.status_code == 201
    r = client.post("/api/financeiro/", headers=h, json={"paciente_id": pac["id"], "valor": 80})
    assert r.status_code == 201
    r = client.post("/api/estoque/itens", headers=h, json={
        "nome": "Luva", "categoria": "Material", "unidade": "cx", "estoque_minimo": 2,
        "quantidade_inicial": 5, "lote": "L1", "validade": "2030-01-01"})
    assert r.status_code == 201
    return dono, recep, pac, h


def test_lista_de_pacientes_so_traz_colunas_da_tela(client, base):
    _, _, pac, h = base
    item = client.get("/api/pacientes/", headers=h).get_json()["items"][0]
    assert set(item) == {"id", "nome", "cpf", "telefone_whatsapp", "status", "ultima_consulta"}
    # dados clínicos e pessoais ficam só na ficha
    completo = client.get(f"/api/pacientes/{pac['id']}", headers=h).get_json()
    assert {"anamnese", "odontograma", "endereco", "data_nascimento"} <= set(completo)


def test_agenda_nao_traz_colunas_internas(client, base):
    _, _, _, h = base
    c = client.get("/api/consultas/", headers=h).get_json()[0]
    assert not {"clinica_id", "updated_by", "created_at", "updated_at"} & set(c)
    assert {"id", "paciente_id", "data_agendada", "status", "pacientes", "dentista"} <= set(c)
    assert c["pacientes"]["nome"] and c["dentista"]["nome"]


def test_financeiro_lista_sem_colunas_internas(client, base):
    _, _, _, h = base
    l = client.get("/api/financeiro/", headers=h).get_json()[0]
    assert "clinica_id" not in l
    assert {"id", "valor", "status_pagamento", "forma_pagamento", "created_at", "pacientes", "dentista"} <= set(l)


def test_estoque_lista_calcula_saldo_com_colunas_minimas(client, base):
    _, _, _, h = base
    item = client.get("/api/estoque/itens", headers=h).get_json()[0]
    assert "clinica_id" not in item and "created_at" not in item
    assert item["quantidade_atual"] == 5 and item["proximo_vencimento"] == "2030-01-01"
    assert item["status"] == "Normal"


def test_equipe_colunas_por_papel(client, base):
    dono, recep, _, h = base
    do_dono = client.get("/api/usuarios/", headers=h).get_json()
    assert all({"permissoes", "percentual_repasse"} <= set(m) for m in do_dono)
    da_recepcao = client.get("/api/usuarios/", headers=auth(recep["token"])).get_json()
    assert all(set(m) <= {"id", "nome", "papel", "cro", "ativo", "clinica_id"} for m in da_recepcao)


def test_lista_de_clinicas_enxuta(client, base):
    _, _, _, h = base
    c = client.get("/api/clinicas/", headers=h).get_json()[0]
    assert set(c) == {"id", "nome_fantasia", "razao_social", "cnpj", "nome", "ativa"}

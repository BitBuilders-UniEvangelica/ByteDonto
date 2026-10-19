"""RF-010 / RNE-008 — item do plano concluído gera cobrança pendente."""

from conftest import auth


def _plano_com_item(client, cenario, quantidade=2, valor_unitario=150.0, dente="36"):
    dono = cenario.dono()
    especialista = cenario.membro(dono, "Especialista")
    paciente = cenario.paciente(dono)
    r = client.post("/api/planos/", json={
        "paciente_id": paciente["id"],
        "titulo": "Plano inicial",
        "itens": [{"procedimento": "Restauração", "dente": dente,
                   "quantidade": quantidade, "valor_unitario": valor_unitario}],
    }, headers=auth(especialista["token"]))
    assert r.status_code == 201, r.get_json()
    plano = r.get_json()
    return dono, especialista, plano, plano["itens"][0]


def _lancamentos_do_item(client, dono, item_id):
    todos = client.get("/api/financeiro/", headers=auth(dono["token"])).get_json()
    return [l for l in todos if l.get("plano_item_id") == item_id]


def _mudar_status(client, quem, plano, item, status):
    return client.put(f"/api/planos/{plano['id']}/itens/{item['id']}",
                      json={"status": status}, headers=auth(quem["token"]))


def test_plano_calcula_valor_total(client, cenario):
    _, _, plano, _ = _plano_com_item(client, cenario, quantidade=2, valor_unitario=150.0)
    assert float(plano["valor_total"]) == 300.0


def test_concluir_item_gera_lancamento_pendente(client, cenario):
    dono, especialista, plano, item = _plano_com_item(client, cenario)

    assert _mudar_status(client, especialista, plano, item, "Concluido").status_code == 200

    lancamentos = _lancamentos_do_item(client, dono, item["id"])
    assert len(lancamentos) == 1
    l = lancamentos[0]
    assert l["status_pagamento"] == "Pendente"
    assert float(l["valor"]) == 300.0
    assert l["descricao"] == "Restauração (dente 36)"
    assert l["dentista_responsavel"] == especialista["id"]


def test_concluir_duas_vezes_nao_duplica_cobranca(client, cenario):
    dono, especialista, plano, item = _plano_com_item(client, cenario)
    _mudar_status(client, especialista, plano, item, "Concluido")
    _mudar_status(client, especialista, plano, item, "Concluido")
    assert len(_lancamentos_do_item(client, dono, item["id"])) == 1


def test_reverter_item_cancela_cobranca_pendente(client, cenario):
    dono, especialista, plano, item = _plano_com_item(client, cenario)
    _mudar_status(client, especialista, plano, item, "Concluido")
    _mudar_status(client, especialista, plano, item, "Pendente")

    lancamentos = _lancamentos_do_item(client, dono, item["id"])
    assert [l["status_pagamento"] for l in lancamentos] == ["Cancelado"]


def test_item_sem_valor_nao_gera_cobranca(client, cenario):
    dono, especialista, plano, item = _plano_com_item(client, cenario, valor_unitario=0)
    _mudar_status(client, especialista, plano, item, "Concluido")
    assert _lancamentos_do_item(client, dono, item["id"]) == []


def test_outra_clinica_nao_altera_item_do_plano(client, cenario):
    _, _, plano, item = _plano_com_item(client, cenario)
    intruso = cenario.dono("Outro Dono")
    assert _mudar_status(client, intruso, plano, item, "Concluido").status_code == 404

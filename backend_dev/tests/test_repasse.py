"""RF-011 / RNE-009 — repasse mensal calculado só sobre lançamentos pagos."""

from conftest import auth


def _lancar(client, dono, paciente, dentista, valor, status):
    r = client.post("/api/financeiro/", json={
        "paciente_id": paciente["id"], "dentista_responsavel": dentista["id"],
        "valor": valor, "status_pagamento": status,
    }, headers=auth(dono["token"]))
    assert r.status_code == 201, r.get_json()
    return r.get_json()


def _repasse_de(client, dono, dentista_id):
    r = client.get("/api/financeiro/repasses", headers=auth(dono["token"]))
    assert r.status_code == 200, r.get_json()
    return next(i for i in r.get_json()["itens"] if i["dentista_id"] == dentista_id)


def test_repasse_aplica_percentual_so_sobre_pagos(client, cenario):
    dono = cenario.dono()
    especialista = cenario.membro(dono, "Especialista", percentual_repasse=40)
    paciente = cenario.paciente(dono)

    _lancar(client, dono, paciente, especialista, 1000, "Pago")
    _lancar(client, dono, paciente, especialista, 500, "Pendente")
    _lancar(client, dono, paciente, especialista, 300, "Cancelado")

    item = _repasse_de(client, dono, especialista["id"])
    assert item["producao"] == 1000.0
    assert item["repasse"] == 400.0


def test_lancamento_pago_depois_entra_no_repasse(client, cenario):
    dono = cenario.dono()
    especialista = cenario.membro(dono, "Especialista", percentual_repasse=50)
    paciente = cenario.paciente(dono)
    lancamento = _lancar(client, dono, paciente, especialista, 200, "Pendente")

    assert _repasse_de(client, dono, especialista["id"])["repasse"] == 0.0

    r = client.put(f"/api/financeiro/{lancamento['id']}", json={"status_pagamento": "Pago"},
                   headers=auth(dono["token"]))
    assert r.status_code == 200
    assert _repasse_de(client, dono, especialista["id"])["repasse"] == 100.0


def test_dentista_sem_producao_aparece_zerado(client, cenario):
    dono = cenario.dono()
    especialista = cenario.membro(dono, "Especialista", percentual_repasse=30)
    item = _repasse_de(client, dono, especialista["id"])
    assert item["producao"] == 0.0 and item["repasse"] == 0.0


def test_mes_invalido_e_recusado(client, cenario):
    dono = cenario.dono()
    r = client.get("/api/financeiro/repasses?mes=2026-13", headers=auth(dono["token"]))
    assert r.status_code == 400


def test_lancamento_recusa_valor_zero(client, cenario):
    dono = cenario.dono()
    paciente = cenario.paciente(dono)
    r = client.post("/api/financeiro/", json={"paciente_id": paciente["id"], "valor": 0},
                    headers=auth(dono["token"]))
    assert r.status_code == 400

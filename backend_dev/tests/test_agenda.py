"""RF-002 e RF-009 — agendamento, mudança de status e cancelamento de consultas."""

import pytest

from conftest import auth


def _agendar(client, quem, **corpo):
    return client.post("/api/consultas/", json=corpo, headers=auth(quem["token"]))


def test_recepcao_agenda_consulta(client, cenario):
    dono = cenario.dono()
    recepcao = cenario.membro(dono, "Recepção")
    especialista = cenario.membro(dono, "Especialista")
    paciente = cenario.paciente(dono)

    r = _agendar(client, recepcao, paciente_id=paciente["id"], dentista_id=especialista["id"],
                 data_agendada="2026-11-10T09:00:00", duracao_minutos=30)
    assert r.status_code == 201
    consulta = r.get_json()
    assert consulta["status"] == "Agendado"
    assert consulta["pacientes"]["nome"] == paciente["nome"]


def test_recusa_duracao_fora_do_limite(client, cenario):
    dono = cenario.dono()
    paciente = cenario.paciente(dono)
    r = _agendar(client, dono, paciente_id=paciente["id"],
                 data_agendada="2026-11-10T09:00:00", duracao_minutos=2)
    assert r.status_code == 400


def test_recusa_status_inexistente(client, cenario):
    dono = cenario.dono()
    paciente = cenario.paciente(dono)
    r = _agendar(client, dono, paciente_id=paciente["id"],
                 data_agendada="2026-11-10T09:00:00", status="Qualquer")
    assert r.status_code == 400


def test_nao_agenda_paciente_de_outra_clinica(client, cenario):
    dono_a = cenario.dono("Dono A")
    dono_b = cenario.dono("Dono B")
    paciente_b = cenario.paciente(dono_b)
    r = _agendar(client, dono_a, paciente_id=paciente_b["id"], data_agendada="2026-11-10T09:00:00")
    assert r.status_code == 404


def test_fluxo_check_in_e_cancelamento(client, cenario):
    dono = cenario.dono()
    paciente = cenario.paciente(dono)
    consulta = _agendar(client, dono, paciente_id=paciente["id"],
                        data_agendada="2026-11-10T09:00:00").get_json()

    r = client.put(f"/api/consultas/{consulta['id']}", json={"status": "Aguardando"},
                   headers=auth(dono["token"]))
    assert r.status_code == 200
    assert r.get_json()["status"] == "Aguardando"

    r = client.delete(f"/api/consultas/{consulta['id']}", headers=auth(dono["token"]))
    assert r.status_code == 200
    lista = client.get("/api/consultas/", headers=auth(dono["token"])).get_json()
    status = {c["id"]: c["status"] for c in lista}
    assert status.get(consulta["id"], "Cancelado") == "Cancelado"


@pytest.mark.xfail(strict=True, reason=(
    "RF-002 prevê validação de sobreposição de horários, mas a rota POST /api/consultas "
    "ainda não verifica conflito. Quando a validação for implementada este teste passa "
    "e o xfail deve ser removido."
))
def test_recusa_dois_horarios_sobrepostos_para_o_mesmo_dentista(client, cenario):
    dono = cenario.dono()
    especialista = cenario.membro(dono, "Especialista")
    p1, p2 = cenario.paciente(dono), cenario.paciente(dono)

    primeira = _agendar(client, dono, paciente_id=p1["id"], dentista_id=especialista["id"],
                        data_agendada="2026-11-10T09:00:00", duracao_minutos=60)
    assert primeira.status_code == 201

    sobreposta = _agendar(client, dono, paciente_id=p2["id"], dentista_id=especialista["id"],
                          data_agendada="2026-11-10T09:30:00", duracao_minutos=30)
    assert sobreposta.status_code == 409

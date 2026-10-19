"""RF-001 e RF-003 — cadastro de pacientes e isolamento entre clínicas."""

from conftest import auth, gerar_cpf

ANAMNESE_OK = {"alergias": "Nega", "medicacoes": "Nenhuma", "condicoes": "Nenhuma"}


def _corpo(**extra):
    corpo = {
        "nome": "Paciente",
        "cpf": gerar_cpf(987654321),
        "telefone_whatsapp": "62999990000",
        "data_nascimento": "1990-05-10",
        "anamnese": dict(ANAMNESE_OK),
    }
    corpo.update(extra)
    return corpo


def test_cadastra_paciente_completo(client, cenario):
    dono = cenario.dono()
    r = client.post("/api/pacientes/", json=_corpo(), headers=auth(dono["token"]))
    assert r.status_code == 201
    assert r.get_json()["clinica_id"] == dono["clinica_id"]


def test_recusa_cpf_invalido(client, cenario):
    dono = cenario.dono()
    r = client.post("/api/pacientes/", json=_corpo(cpf="11111111111"), headers=auth(dono["token"]))
    assert r.status_code == 400


def test_exige_anamnese_minima(client, cenario):
    """Sem alergias/medicações/condições declaradas o cadastro é bloqueado."""
    dono = cenario.dono()
    r = client.post("/api/pacientes/", json=_corpo(anamnese={"alergias": "Nega"}),
                    headers=auth(dono["token"]))
    assert r.status_code == 400
    assert "Anamnese incompleta" in r.get_json()["error"]


def test_recusa_data_de_nascimento_no_futuro(client, cenario):
    dono = cenario.dono()
    r = client.post("/api/pacientes/", json=_corpo(data_nascimento="2999-01-01"),
                    headers=auth(dono["token"]))
    assert r.status_code == 400


def test_clinica_nao_ve_paciente_de_outra_clinica(client, cenario):
    dono_a = cenario.dono("Dono A")
    dono_b = cenario.dono("Dono B")
    paciente_a = cenario.paciente(dono_a)

    r = client.get(f"/api/pacientes/{paciente_a['id']}", headers=auth(dono_b["token"]))
    assert r.status_code == 404

    lista_b = client.get("/api/pacientes/", headers=auth(dono_b["token"])).get_json()
    assert paciente_a["id"] not in [p["id"] for p in lista_b]

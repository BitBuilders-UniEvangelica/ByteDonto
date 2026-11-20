"""Ações permitidas que gravam no prontuário (banco limpo por teste) e a
rastreabilidade (auditoria) dessas alterações."""

import pytest

from apoio import auth, consultar

pytestmark = [pytest.mark.prontuario, pytest.mark.rbac]


@pytest.fixture
def base(cenario):
    dono = cenario.dono()
    return dono, cenario.membro(dono, "Recepção"), cenario.membro(dono, "Especialista"), cenario.paciente(dono)


def test_recepcao_cadastra_e_edita_cadastro_e_anamnese(client, cenario, base):
    dono, recep, espec, pac = base
    h = auth(recep["token"])
    novo = cenario.paciente(recep)
    assert novo["id"]
    r = client.put(f"/api/pacientes/{pac['id']}", headers=h,
                   json={"telefone_whatsapp": "62988887777", "anamnese": {"alergias": "Látex"}})
    assert r.status_code == 200, r.get_json()
    assert "odontograma" not in r.get_json()


def test_especialista_edita_anamnese_e_odontograma(client, base):
    dono, recep, espec, pac = base
    h = auth(espec["token"])
    assert client.put(f"/api/pacientes/{pac['id']}", headers=h, json={"anamnese": {"alergias": "Látex"}}).status_code == 200
    r = client.put(f"/api/pacientes/{pac['id']}", headers=h, json={"odontograma": {"11": "restaurado"}})
    assert r.status_code == 200 and r.get_json()["odontograma"] == {"11": "restaurado"}


def test_dono_inativa_e_exclui_paciente(client, base):
    dono, recep, espec, pac = base
    h = auth(dono["token"])
    assert client.put(f"/api/pacientes/{pac['id']}", headers=h, json={"status": "Inativo"}).status_code == 200
    assert client.delete(f"/api/pacientes/{pac['id']}", headers=h).status_code == 200
    assert client.get(f"/api/pacientes/{pac['id']}", headers=h).status_code == 404


def test_alteracoes_do_prontuario_ficam_na_auditoria(client, base):
    dono, recep, espec, pac = base
    client.put(f"/api/pacientes/{pac['id']}", headers=auth(espec["token"]), json={"odontograma": {"11": "carie"}})
    client.put(f"/api/pacientes/{pac['id']}", headers=auth(recep["token"]), json={"anamnese": {"alergias": "Látex"}})
    linhas = consultar("SELECT usuario_id::text, acao, campos FROM auditoria_prontuario "
                       "WHERE tabela = 'pacientes' AND registro_id = %s ORDER BY id", [pac["id"]])
    assert [l[1] for l in linhas] == ["INSERT", "UPDATE", "UPDATE"]
    assert linhas[1][0] == espec["id"] and "odontograma" in linhas[1][2]
    assert linhas[2][0] == recep["id"] and "anamnese" in linhas[2][2]

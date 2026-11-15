"""Seção 25.3 — permissões por perfil checadas no servidor.

A tela esconde o que cada papel não pode fazer, mas a API também precisa
barrar: estes testes chamam a API direto, como faria alguém fora da tela.
"""

from conftest import auth


def _consulta(client, quem, paciente, dentista):
    r = client.post("/api/consultas/", json={
        "paciente_id": paciente["id"],
        "dentista_id": dentista["id"],
        "data_agendada": "2030-01-10T09:00:00",
    }, headers=auth(quem["token"]))
    assert r.status_code == 201, r.get_json()
    return r.get_json()


def _permissoes(client, dono, membro, **permissoes):
    r = client.patch(f"/api/usuarios/{membro['id']}/permissoes",
                     json={"permissoes": permissoes}, headers=auth(dono["token"]))
    assert r.status_code == 200, r.get_json()


# ---------------- Pacientes ----------------

def test_especialista_nao_cadastra_paciente(client, cenario):
    dono = cenario.dono()
    esp = cenario.membro(dono, "Especialista")
    r = client.post("/api/pacientes/", json={"nome": "X"}, headers=auth(esp["token"]))
    assert r.status_code == 403


def test_especialista_nao_edita_cadastro_mas_edita_odontograma(client, cenario):
    dono = cenario.dono()
    esp = cenario.membro(dono, "Especialista")
    pac = cenario.paciente(dono)

    r = client.put(f"/api/pacientes/{pac['id']}", json={"telefone_whatsapp": "62988887777"},
                   headers=auth(esp["token"]))
    assert r.status_code == 403

    r = client.put(f"/api/pacientes/{pac['id']}", json={"odontograma": {"11": "cárie"}},
                   headers=auth(esp["token"]))
    assert r.status_code == 200


def test_recepcao_nao_edita_odontograma_mas_edita_cadastro(client, cenario):
    dono = cenario.dono()
    rec = cenario.membro(dono, "Recepção")
    pac = cenario.paciente(rec)

    r = client.put(f"/api/pacientes/{pac['id']}", json={"odontograma": {"11": "cárie"}},
                   headers=auth(rec["token"]))
    assert r.status_code == 403

    r = client.put(f"/api/pacientes/{pac['id']}", json={"telefone_whatsapp": "62988887777"},
                   headers=auth(rec["token"]))
    assert r.status_code == 200


def test_anamnese_vale_para_recepcao_e_especialista(client, cenario):
    dono = cenario.dono()
    rec = cenario.membro(dono, "Recepção")
    esp = cenario.membro(dono, "Especialista")
    pac = cenario.paciente(dono)
    anamnese = {"alergias": "Dipirona", "medicacoes": "Nenhuma", "condicoes": "Nenhuma"}
    for quem in (rec, esp):
        r = client.put(f"/api/pacientes/{pac['id']}", json={"anamnese": anamnese},
                       headers=auth(quem["token"]))
        assert r.status_code == 200, r.get_json()


def test_so_o_dono_remove_paciente(client, cenario):
    dono = cenario.dono()
    rec = cenario.membro(dono, "Recepção")
    pac = cenario.paciente(dono)

    r = client.delete(f"/api/pacientes/{pac['id']}", headers=auth(rec["token"]))
    assert r.status_code == 403

    r = client.delete(f"/api/pacientes/{pac['id']}", headers=auth(dono["token"]))
    assert r.status_code == 200


def test_sem_ver_pacientes_nao_lista_nem_abre(client, cenario):
    dono = cenario.dono()
    rec = cenario.membro(dono, "Recepção")
    pac = cenario.paciente(dono)
    _permissoes(client, dono, rec, ver_pacientes=False)

    assert client.get("/api/pacientes/", headers=auth(rec["token"])).status_code == 403
    assert client.get(f"/api/pacientes/{pac['id']}", headers=auth(rec["token"])).status_code == 403


# ---------------- Agenda ----------------

def test_sem_ver_agenda_nao_lista_consultas(client, cenario):
    dono = cenario.dono()
    rec = cenario.membro(dono, "Recepção")
    _permissoes(client, dono, rec, ver_agenda=False)
    assert client.get("/api/consultas/", headers=auth(rec["token"])).status_code == 403


def test_recepcao_nao_escreve_evolucao_clinica(client, cenario):
    dono = cenario.dono()
    rec = cenario.membro(dono, "Recepção")
    esp = cenario.membro(dono, "Especialista")
    consulta = _consulta(client, rec, cenario.paciente(rec), esp)

    r = client.put(f"/api/consultas/{consulta['id']}", json={"evolucao_clinica": "Restauração"},
                   headers=auth(rec["token"]))
    assert r.status_code == 403

    # check-in continua liberado para a recepção
    r = client.put(f"/api/consultas/{consulta['id']}", json={"status": "Aguardando"},
                   headers=auth(rec["token"]))
    assert r.status_code == 200


def test_especialista_nao_remarca_nem_cancela_mas_finaliza(client, cenario):
    dono = cenario.dono()
    esp = cenario.membro(dono, "Especialista")
    consulta = _consulta(client, dono, cenario.paciente(dono), esp)
    url = f"/api/consultas/{consulta['id']}"

    r = client.put(url, json={"data_agendada": "2030-01-11T09:00:00"}, headers=auth(esp["token"]))
    assert r.status_code == 403
    r = client.put(url, json={"status": "Cancelado"}, headers=auth(esp["token"]))
    assert r.status_code == 403

    r = client.put(url, json={"evolucao_clinica": "Profilaxia", "status": "Finalizado"},
                   headers=auth(esp["token"]))
    assert r.status_code == 200


# ---------------- Prontuário: planos e imagens ----------------

def test_recepcao_nao_ve_nem_cria_plano_de_tratamento(client, cenario):
    dono = cenario.dono()
    rec = cenario.membro(dono, "Recepção")
    pac = cenario.paciente(dono)

    r = client.get(f"/api/planos/?paciente_id={pac['id']}", headers=auth(rec["token"]))
    assert r.status_code == 403
    r = client.post("/api/planos/", json={"paciente_id": pac["id"], "titulo": "Plano"},
                    headers=auth(rec["token"]))
    assert r.status_code == 403


def test_sem_permissao_de_edicao_nao_envia_arquivo(client, cenario):
    dono = cenario.dono()
    esp = cenario.membro(dono, "Especialista")
    pac = cenario.paciente(dono)
    _permissoes(client, dono, esp, editar_prontuario=False)

    r = client.post("/api/imagens/upload", data={"paciente_id": pac["id"]},
                    headers=auth(esp["token"]))
    assert r.status_code == 403


# ---------------- Clínica, equipe e painel ----------------

def test_so_o_dono_altera_os_dados_da_clinica(client, cenario):
    dono = cenario.dono()
    rec = cenario.membro(dono, "Recepção")
    r = client.put(f"/api/clinicas/{dono['clinica_id']}", json={"nome": "Outra"},
                   headers=auth(rec["token"]))
    assert r.status_code == 403


def test_equipe_esconde_permissoes_e_repasse_de_quem_nao_e_dono(client, cenario):
    dono = cenario.dono()
    esp = cenario.membro(dono, "Especialista", percentual_repasse=40)

    r = client.get("/api/usuarios/", headers=auth(esp["token"]))
    assert r.status_code == 200
    for membro in r.get_json():
        assert "permissoes" not in membro
        assert "percentual_repasse" not in membro

    r = client.get("/api/usuarios/", headers=auth(dono["token"]))
    assert any("permissoes" in m for m in r.get_json())


def test_painel_nao_mostra_receita_para_quem_nao_ve_financeiro(client, cenario):
    dono = cenario.dono()
    esp = cenario.membro(dono, "Especialista")
    r = client.post("/api/financeiro/", json={
        "paciente_id": cenario.paciente(dono)["id"],
        "descricao": "Consulta", "valor": 150, "status_pagamento": "Pago",
    }, headers=auth(dono["token"]))
    assert r.status_code == 201, r.get_json()
    assert client.get("/api/dashboard/metricas", headers=auth(dono["token"])).get_json()["receita_mes"] == 150

    metricas = client.get("/api/dashboard/metricas", headers=auth(esp["token"])).get_json()
    assert metricas["receita_mes"] == 0
    assert metricas["pendente_mes"] == 0

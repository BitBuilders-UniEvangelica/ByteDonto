"""RBAC — fluxos permitidos e permissões configuradas pelo Dono (banco limpo por teste).

Tudo real: contas criadas por /api/auth/registro e /api/usuarios/criar,
tokens emitidos pelo /api/auth/login, dados gravados pelas rotas no PostgreSQL.
Nenhuma permissão extra é concedida para "passar" — os membros usam
exatamente PERMISSOES_PADRAO (o que /api/usuarios/criar grava).
"""

import io

import pytest

pytestmark = pytest.mark.rbac

from apoio import auth, consultar, executar

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
PDF = b"%PDF-1.7\n" + b"0" * 64


# ---- O que cada papel PODE fazer (o RBAC não quebra o fluxo atual) ----------
# Estes testes alteram dados: rodam com o banco limpo e cenário próprio.

PNG_LIVRE = PNG


def _base(cenario):
    dono = cenario.dono()
    return dono, cenario.membro(dono, "Recepção"), cenario.membro(dono, "Especialista"), cenario.paciente(dono)


def test_recepcao_fluxos_permitidos(client, cenario):
    dono, recep, espec, pac = _base(cenario)
    h = auth(recep["token"])
    consulta = client.post("/api/consultas/", headers=h, json={
        "paciente_id": pac["id"], "dentista_id": espec["id"], "data_agendada": "2026-01-10T10:00:00"})
    assert consulta.status_code == 201, consulta.get_json()
    assert client.get("/api/pacientes/", headers=h).status_code == 200
    r = client.put(f"/api/pacientes/{pac['id']}", headers=h, json={"rg": "123", "anamnese": {"alergias": "Dipirona"}})
    assert r.status_code == 200, r.get_json()
    for status in ("Aguardando", "Faltou", "Cancelado"):
        r = client.put(f"/api/consultas/{consulta.get_json()['id']}", headers=h, json={"status": status})
        assert r.status_code == 200, (status, r.get_json())
    assert client.get("/api/financeiro/", headers=h).status_code == 200
    r = client.post("/api/imagens/upload", headers=h, content_type="multipart/form-data", data={
        "paciente_id": pac["id"], "tipo": "termo_consentimento", "file": (io.BytesIO(PDF), "termo.pdf")})
    assert r.status_code == 201, r.get_json()
    # estoque é permitido à recepção por padrão
    assert client.get("/api/estoque/itens", headers=h).status_code == 200
    assert client.post("/api/estoque/fornecedores", headers=h, json={"nome": "F1"}).status_code == 201


def test_especialista_fluxos_permitidos(client, cenario):
    dono, recep, espec, pac = _base(cenario)
    h, pid = auth(espec["token"]), pac["id"]
    consulta = client.post("/api/consultas/", headers=auth(dono["token"]), json={
        "paciente_id": pid, "dentista_id": espec["id"], "data_agendada": "2026-01-10T10:00:00"}).get_json()
    assert client.get(f"/api/planos/?paciente_id={pid}", headers=h).status_code == 200
    assert client.put(f"/api/pacientes/{pid}", headers=h, json={"odontograma": {"11": "restaurado"}}).status_code == 200
    assert client.put(f"/api/pacientes/{pid}", headers=h, json={"anamnese": {"alergias": "Nega"}}).status_code == 200
    plano = client.post("/api/planos/", headers=h, json={"paciente_id": pid, "itens": [{"procedimento": "X", "valor_unitario": 10}]})
    assert plano.status_code == 201, plano.get_json()
    plano = plano.get_json()
    r = client.put(f"/api/planos/{plano['id']}/itens/{plano['itens'][0]['id']}", headers=h, json={"status": "Concluido"})
    assert r.status_code == 200
    r = client.put(f"/api/consultas/{consulta['id']}", headers=h, json={
        "procedimentos_descritos": "Resina", "evolucao_clinica": "Ok", "status": "Finalizado"})
    assert r.status_code == 200, r.get_json()
    r = client.post("/api/imagens/upload", headers=h, content_type="multipart/form-data", data={
        "paciente_id": pid, "tipo": "imagem", "file": (io.BytesIO(PNG_LIVRE), "rx.png")})
    assert r.status_code == 201
    assert client.get("/api/dashboard/metricas", headers=h).status_code == 200
    assert client.post("/api/esterilizacao/equipamentos", headers=h, json={"identificacao": "AUTO-01"}).status_code == 201
    assert client.get("/api/estoque/itens", headers=h).status_code == 200


def test_dono_tem_acesso_total_na_propria_clinica(client, cenario):
    dono, recep, espec, pac = _base(cenario)
    h, pid = auth(dono["token"]), pac["id"]
    assert client.get(f"/api/planos/?paciente_id={pid}", headers=h).status_code == 200
    assert client.get("/api/financeiro/repasses", headers=h).status_code == 200
    assert client.put(f"/api/clinicas/{dono['clinica_id']}", headers=h, json={"nome": "Clínica A+"}).status_code == 200
    img = client.post("/api/imagens/upload", headers=h, content_type="multipart/form-data", data={
        "paciente_id": pid, "tipo": "imagem", "file": (io.BytesIO(PNG), "rx.png")}).get_json()
    assert client.delete(f"/api/imagens/{img['id']}", headers=h).status_code == 200
    assert client.delete(f"/api/pacientes/{pid}", headers=h).status_code == 200
    assert client.get("/api/esterilizacao/ciclos", headers=h).status_code == 200


# ---- Permissões individuais configuradas pelo Dono --------------------------

def test_permissao_revogada_pelo_dono_e_respeitada(client, cenario):
    dono, recep, espec, pac = _base(cenario)
    r = client.patch(f"/api/usuarios/{espec['id']}/permissoes", headers=auth(dono["token"]),
                     json={"permissoes": {"ver_prontuario": False, "estoque": False}})
    assert r.status_code == 200, r.get_json()
    assert client.get(f"/api/planos/?paciente_id={pac['id']}", headers=auth(espec["token"])).status_code == 403
    assert client.get("/api/estoque/itens", headers=auth(espec["token"])).status_code == 403


def test_permissao_concedida_pelo_dono_e_respeitada(client, cenario):
    dono, recep, espec, pac = _base(cenario)
    assert client.get("/api/esterilizacao/ciclos", headers=auth(recep["token"])).status_code == 403
    r = client.patch(f"/api/usuarios/{recep['id']}/permissoes", headers=auth(dono["token"]),
                     json={"permissoes": {"esterilizacao": True}})
    assert r.status_code == 200, r.get_json()
    assert client.get("/api/esterilizacao/ciclos", headers=auth(recep["token"])).status_code == 200


def test_perfil_sem_permissoes_cai_no_padrao_do_papel(client, cenario):
    """Membros antigos (sem as chaves novas no JSON) usam o padrão do papel."""
    dono, recep, espec, pac = _base(cenario)
    executar("UPDATE usuarios SET permissoes = '{}'::jsonb WHERE id = %s", [recep["id"]])
    assert client.get(f"/api/planos/?paciente_id={pac['id']}", headers=auth(recep["token"])).status_code == 403
    assert client.get("/api/esterilizacao/ciclos", headers=auth(recep["token"])).status_code == 403
    assert client.get("/api/pacientes/", headers=auth(recep["token"])).status_code == 200
    assert client.get("/api/estoque/itens", headers=auth(recep["token"])).status_code == 200


def test_usuario_desativado_e_bloqueado_mesmo_com_token_valido(client, cenario):
    dono, recep, espec, pac = _base(cenario)
    r = client.put(f"/api/usuarios/{recep['id']}", headers=auth(dono["token"]), json={"ativo": False})
    assert r.status_code == 200, r.get_json()
    assert client.get("/api/pacientes/", headers=auth(recep["token"])).status_code == 403
    assert client.get("/api/estoque/itens", headers=auth(recep["token"])).status_code == 403

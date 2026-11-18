"""Isolamento entre clínicas: o Dono da clínica A não lê nem altera nada da B.

Cobre os módulos antigos (pacientes, planos, agenda, financeiro, imagens,
clínicas, dashboard) e os migrados (estoque e esterilização), incluindo IDs
da outra clínica enviados no corpo (IDOR).
"""

import io
from datetime import date

import pytest

from apoio import auth, consultar, foto_do_banco

pytestmark = pytest.mark.isolamento

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
HOJE = date.today().isoformat()


@pytest.fixture
def duas_clinicas(client, cenario):
    a, b = cenario.dono("Dono A"), cenario.dono("Dono B")
    hb = auth(b["token"])
    pac_b = cenario.paciente(b)
    forn_b = client.post("/api/estoque/fornecedores", headers=hb, json={"nome": "Forn B"}).get_json()
    item_b = client.post("/api/estoque/itens", headers=hb, json={
        "nome": "Luva B", "categoria": "Material", "unidade": "cx", "estoque_minimo": 1,
        "quantidade_inicial": 10, "lote": "LB", "validade": "2030-01-01"}).get_json()
    lote_b = client.get(f"/api/estoque/itens/{item_b['id']}", headers=hb).get_json()["lotes"][0]
    equip_b = client.post("/api/esterilizacao/equipamentos", headers=hb, json={"identificacao": "AUTO-B"}).get_json()
    ciclo_b = client.post("/api/esterilizacao/ciclos", headers=hb, json={
        "equipamento_id": equip_b["id"], "iniciado_em": f"{HOJE}T08:00:00", "temperatura_c": 134,
        "pressao_kgf_cm2": 2.1, "tempo_exposicao_min": 7,
        "pacotes": [{"conteudo": "Kit B", "validade_dias": 30}]}).get_json()
    img_b = client.post("/api/imagens/upload", headers=hb, content_type="multipart/form-data", data={
        "paciente_id": pac_b["id"], "tipo": "imagem", "file": (io.BytesIO(PNG), "rx.png")}).get_json()
    return a, b, dict(pac=pac_b, forn=forn_b, item=item_b, lote=lote_b, equip=equip_b, ciclo=ciclo_b, img=img_b)


def test_modulos_antigos_isolados(client, cenario, duas_clinicas):
    a, b, x = duas_clinicas
    h = auth(a["token"])
    pb = x["pac"]["id"]
    antes = foto_do_banco()
    assert client.get(f"/api/pacientes/{pb}", headers=h).status_code == 404
    assert client.put(f"/api/pacientes/{pb}", headers=h, json={"nome": "X"}).status_code == 404
    assert client.delete(f"/api/pacientes/{pb}", headers=h).status_code == 404
    assert client.post("/api/planos/", headers=h, json={"paciente_id": pb}).status_code == 404
    assert client.post("/api/consultas/", headers=h, json={"paciente_id": pb, "data_agendada": "2026-02-01T10:00"}).status_code == 404
    assert client.post("/api/financeiro/", headers=h, json={"paciente_id": pb, "valor": 10}).status_code == 404
    assert client.put(f"/api/clinicas/{b['clinica_id']}", headers=h, json={"nome": "X"}).status_code == 403
    assert client.get(f"/api/clinicas/{b['clinica_id']}", headers=h).status_code == 403
    assert client.get(f"/api/dashboard/metricas?clinica_id={b['clinica_id']}", headers=h).status_code == 403
    assert client.get(f"/api/imagens/?paciente_id={pb}", headers=h).get_json() == []
    assert client.delete(f"/api/imagens/{x['img']['id']}", headers=h).status_code == 404
    r = client.post("/api/imagens/upload", headers=h, content_type="multipart/form-data", data={
        "paciente_id": pb, "tipo": "imagem", "file": (io.BytesIO(PNG), "rx.png")})
    assert r.status_code == 403
    assert client.get("/api/pacientes/", headers=h).get_json() == []
    assert foto_do_banco() == antes


def test_estoque_isolado(client, cenario, duas_clinicas):
    a, b, x = duas_clinicas
    h = auth(a["token"])
    item_a = client.post("/api/estoque/itens", headers=h, json={
        "nome": "Luva A", "categoria": "Material", "unidade": "cx", "estoque_minimo": 1}).get_json()
    antes = foto_do_banco()

    assert client.get("/api/estoque/itens", headers=h).get_json()[0]["id"] == item_a["id"]
    assert len(client.get("/api/estoque/itens", headers=h).get_json()) == 1
    assert client.get("/api/estoque/fornecedores", headers=h).get_json() == []
    assert client.get("/api/estoque/movimentacoes", headers=h).get_json() == []
    assert client.get(f"/api/estoque/itens/{x['item']['id']}", headers=h).status_code == 404
    assert client.put(f"/api/estoque/itens/{x['item']['id']}", headers=h, json={"nome": "X"}).status_code == 404
    assert client.delete(f"/api/estoque/itens/{x['item']['id']}", headers=h).status_code == 404
    assert client.put(f"/api/estoque/fornecedores/{x['forn']['id']}", headers=h, json={"nome": "X"}).status_code == 404
    # IDOR no corpo: item/lote/fornecedor/paciente/responsável de outra clínica
    entrada = {"item_id": x["item"]["id"], "quantidade": 5, "lote": "L", "validade": "2030-01-01",
               "fornecedor_id": x["forn"]["id"], "data": HOJE}
    assert client.post("/api/estoque/entradas", headers=h, json=entrada).status_code in (400, 404)
    entrada_mista = {**entrada, "item_id": item_a["id"]}  # item meu, fornecedor da B
    assert client.post("/api/estoque/entradas", headers=h, json=entrada_mista).status_code == 400
    saida = {"item_id": x["item"]["id"], "lote_id": x["lote"]["id"], "quantidade": 1,
             "motivo": "Uso em procedimento", "data": HOJE, "responsavel_id": a["id"]}
    assert client.post("/api/estoque/saidas", headers=h, json=saida).status_code == 404
    saida_mista = {**saida, "item_id": item_a["id"]}  # item meu, lote da B
    assert client.post("/api/estoque/saidas", headers=h, json=saida_mista).status_code == 404
    assert client.post("/api/estoque/saidas", headers=h, json={**saida, "responsavel_id": b["id"]}).status_code == 400
    assert client.post("/api/estoque/itens", headers=h, json={
        "nome": "Y", "categoria": "Material", "unidade": "cx", "estoque_minimo": 1,
        "fornecedor_id": x["forn"]["id"]}).status_code == 400
    assert foto_do_banco() == antes
    # o saldo da clínica B não mudou
    assert consultar("SELECT quantidade FROM lotes_estoque WHERE id = %s", [x["lote"]["id"]])[0][0] == 10


def test_esterilizacao_isolada(client, cenario, duas_clinicas):
    a, b, x = duas_clinicas
    h = auth(a["token"])
    antes = foto_do_banco()
    assert client.get("/api/esterilizacao/equipamentos", headers=h).get_json() == []
    assert client.get("/api/esterilizacao/ciclos", headers=h).get_json() == []
    assert client.get("/api/esterilizacao/pacotes", headers=h).get_json() == []
    assert client.get(f"/api/esterilizacao/ciclos?equipamento_id={x['equip']['id']}", headers=h).get_json() == []
    assert client.get(f"/api/esterilizacao/pacotes?ciclo_id={x['ciclo']['id']}", headers=h).get_json() == []
    assert client.get(f"/api/esterilizacao/ciclos/{x['ciclo']['id']}", headers=h).status_code == 404
    assert client.put(f"/api/esterilizacao/equipamentos/{x['equip']['id']}", headers=h, json={"ativo": False}).status_code == 404
    assert client.put(f"/api/esterilizacao/ciclos/{x['ciclo']['id']}/indicadores", headers=h,
                      json={"indicador_quimico": "Reprovado"}).status_code == 404
    assert client.post(f"/api/esterilizacao/ciclos/{x['ciclo']['id']}/pacotes", headers=h,
                       json={"pacotes": [{"conteudo": "X", "validade_dias": 5}]}).status_code == 404
    assert client.post("/api/esterilizacao/ciclos", headers=h, json={
        "equipamento_id": x["equip"]["id"], "iniciado_em": f"{HOJE}T08:00:00", "temperatura_c": 134,
        "pressao_kgf_cm2": 2.1, "tempo_exposicao_min": 7}).status_code == 404
    assert foto_do_banco() == antes


def test_banco_recusa_referencia_cruzada_mesmo_sem_a_api(client, cenario, duas_clinicas):
    """Defesa em profundidade: o trigger da migration barra a gravação direta
    (ex.: um bug futuro na rota) de lote apontando para item de outra clínica."""
    import psycopg
    from apoio import executar
    a, b, x = duas_clinicas
    with pytest.raises(psycopg.errors.ForeignKeyViolation, match="CLINICA_DIVERGENTE"):
        executar("INSERT INTO lotes_estoque (clinica_id, item_id, quantidade) VALUES (%s, %s, 1)",
                 [a["clinica_id"], x["item"]["id"]])
    with pytest.raises(psycopg.errors.ForeignKeyViolation, match="CLINICA_DIVERGENTE"):
        executar("INSERT INTO pacotes_esterilizados (clinica_id, ciclo_id, codigo, conteudo, data_esterilizacao, "
                 "data_limite_uso) VALUES (%s, %s, 'X', 'X', CURRENT_DATE, CURRENT_DATE)",
                 [a["clinica_id"], x["ciclo"]["id"]])

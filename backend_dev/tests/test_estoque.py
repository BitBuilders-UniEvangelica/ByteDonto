"""Estoque — itens, lotes, entradas, saídas, histórico e resumo."""

from datetime import date, timedelta

from conftest import auth

BASE = "/api/estoque"
HOJE = date.today().isoformat()


def _fornecedor(client, quem, nome="Dental Sul"):
    r = client.post(f"{BASE}/fornecedores", json={"nome": nome}, headers=auth(quem["token"]))
    assert r.status_code == 201, r.get_json()
    return r.get_json()


def _item(client, quem, **extra):
    corpo = {"nome": "Luva de Procedimento M", "categoria": "Material", "unidade": "cx", "estoque_minimo": 10}
    corpo.update(extra)
    r = client.post(f"{BASE}/itens", json=corpo, headers=auth(quem["token"]))
    assert r.status_code == 201, r.get_json()
    return r.get_json()


def _entrada(client, quem, item, fornecedor, **extra):
    corpo = {
        "item_id": item["id"], "quantidade": 20, "lote": "L001",
        "validade": (date.today() + timedelta(days=200)).isoformat(),
        "fornecedor_id": fornecedor["id"], "data": HOJE,
    }
    corpo.update(extra)
    return client.post(f"{BASE}/entradas", json=corpo, headers=auth(quem["token"]))


def _saida(client, quem, item, lote_id, **extra):
    corpo = {
        "item_id": item["id"], "lote_id": lote_id, "quantidade": 3,
        "motivo": "Uso em procedimento", "data": HOJE, "responsavel_id": quem["id"],
    }
    corpo.update(extra)
    return client.post(f"{BASE}/saidas", json=corpo, headers=auth(quem["token"]))


def _detalhe(client, quem, item):
    r = client.get(f"{BASE}/itens/{item['id']}", headers=auth(quem["token"]))
    assert r.status_code == 200, r.get_json()
    return r.get_json()


def test_item_novo_sem_saldo_fica_esgotado(client, cenario):
    dono = cenario.dono()
    item = _item(client, dono)
    assert item["quantidade_atual"] == 0
    assert item["status"] == "Esgotado"


def test_quantidade_inicial_cria_lote_e_movimentacao(client, cenario):
    dono = cenario.dono()
    item = _item(client, dono, quantidade_inicial=15, lote="ABC", validade="2027-03-15")
    assert item["quantidade_atual"] == 15
    assert item["status"] == "Normal"

    det = _detalhe(client, dono, item)
    assert [(l["lote"], l["quantidade"]) for l in det["lotes"]] == [("ABC", 15)]
    assert det["movimentacoes"][0]["tipo"] == "Entrada"
    assert det["movimentacoes"][0]["motivo"] == "Estoque inicial"


def test_valida_campos_obrigatorios_do_item(client, cenario):
    dono = cenario.dono()
    r = client.post(f"{BASE}/itens", json={"nome": "X", "categoria": "Outro", "unidade": "un", "estoque_minimo": 1},
                    headers=auth(dono["token"]))
    assert r.status_code == 400
    r = client.post(f"{BASE}/itens", json={"nome": "X", "categoria": "Insumo", "unidade": "un"},
                    headers=auth(dono["token"]))
    assert r.status_code == 400


def test_entrada_soma_no_mesmo_lote_e_cria_lote_novo_quando_diferente(client, cenario):
    dono = cenario.dono()
    forn = _fornecedor(client, dono)
    item = _item(client, dono)

    assert _entrada(client, dono, item, forn).status_code == 201
    assert _entrada(client, dono, item, forn, quantidade=5).status_code == 201
    assert _entrada(client, dono, item, forn, lote="L002", quantidade=4).status_code == 201

    det = _detalhe(client, dono, item)
    assert sorted((l["lote"], l["quantidade"]) for l in det["lotes"]) == [("L001", 25), ("L002", 4)]
    assert det["quantidade_atual"] == 29
    assert len(det["movimentacoes"]) == 3


def test_entrada_exige_lote_validade_fornecedor_e_data_nao_futura(client, cenario):
    dono = cenario.dono()
    forn = _fornecedor(client, dono)
    item = _item(client, dono)
    assert _entrada(client, dono, item, forn, lote="").status_code == 400
    assert _entrada(client, dono, item, forn, validade=None).status_code == 400
    assert _entrada(client, dono, item, forn, fornecedor_id=None).status_code == 400
    amanha = (date.today() + timedelta(days=1)).isoformat()
    assert _entrada(client, dono, item, forn, data=amanha).status_code == 400
    assert _entrada(client, dono, item, forn, quantidade=0).status_code == 400


def test_saida_baixa_o_lote_e_muda_status(client, cenario):
    dono = cenario.dono()
    forn = _fornecedor(client, dono)
    item = _item(client, dono, estoque_minimo=10)
    lote = _entrada(client, dono, item, forn, quantidade=12).get_json()["lote"]
    paciente = cenario.paciente(dono)

    r = _saida(client, dono, item, lote["id"], quantidade=3, paciente_id=paciente["id"], procedimento="Restauração 36")
    assert r.status_code == 201, r.get_json()

    det = _detalhe(client, dono, item)
    assert det["quantidade_atual"] == 9
    assert det["status"] == "Estoque baixo"
    saida = det["movimentacoes"][0]
    assert saida["tipo"] == "Saída"
    assert saida["paciente"]["nome"] == paciente["nome"]
    assert saida["lote"]["lote"] == "L001"


def test_saida_nao_passa_do_saldo_do_lote(client, cenario):
    dono = cenario.dono()
    forn = _fornecedor(client, dono)
    item = _item(client, dono)
    lote = _entrada(client, dono, item, forn, quantidade=2).get_json()["lote"]
    r = _saida(client, dono, item, lote["id"], quantidade=3)
    assert r.status_code == 409
    assert _detalhe(client, dono, item)["quantidade_atual"] == 2


def test_lote_zerado_some_dos_lotes_do_item(client, cenario):
    dono = cenario.dono()
    forn = _fornecedor(client, dono)
    item = _item(client, dono)
    lote = _entrada(client, dono, item, forn, quantidade=2).get_json()["lote"]
    assert _saida(client, dono, item, lote["id"], quantidade=2).status_code == 201
    det = _detalhe(client, dono, item)
    assert det["lotes"] == []
    assert det["status"] == "Esgotado"


def test_saida_exige_motivo_valido_e_responsavel_da_clinica(client, cenario):
    dono = cenario.dono()
    outro = cenario.dono("Outra Clínica")
    forn = _fornecedor(client, dono)
    item = _item(client, dono)
    lote = _entrada(client, dono, item, forn).get_json()["lote"]
    assert _saida(client, dono, item, lote["id"], motivo="Qualquer").status_code == 400
    assert _saida(client, dono, item, lote["id"], responsavel_id=outro["id"]).status_code == 400


def test_remover_item_inativa_e_preserva_historico(client, cenario):
    dono = cenario.dono()
    item = _item(client, dono, quantidade_inicial=5)
    r = client.delete(f"{BASE}/itens/{item['id']}", headers=auth(dono["token"]))
    assert r.status_code == 200

    lista = client.get(f"{BASE}/itens", headers=auth(dono["token"])).get_json()
    assert lista == []
    movs = client.get(f"{BASE}/movimentacoes?item_id={item['id']}", headers=auth(dono["token"])).get_json()
    assert len(movs) == 1


def test_editar_item_nao_altera_saldo(client, cenario):
    dono = cenario.dono()
    item = _item(client, dono, quantidade_inicial=5)
    r = client.put(f"{BASE}/itens/{item['id']}", json={"estoque_minimo": 8, "localizacao": "Armário 2"},
                   headers=auth(dono["token"]))
    assert r.status_code == 200, r.get_json()
    atualizado = r.get_json()
    assert atualizado["quantidade_atual"] == 5
    assert atualizado["status"] == "Estoque baixo"
    assert atualizado["localizacao"] == "Armário 2"


def test_resumo_traz_mais_consumidos_e_movimentacoes_do_mes(client, cenario):
    dono = cenario.dono()
    forn = _fornecedor(client, dono)
    luva = _item(client, dono)
    soro = _item(client, dono, nome="Soro Fisiológico", categoria="Insumo", unidade="frasco")
    lote_luva = _entrada(client, dono, luva, forn).get_json()["lote"]
    lote_soro = _entrada(client, dono, soro, forn).get_json()["lote"]
    _saida(client, dono, luva, lote_luva["id"], quantidade=2)
    _saida(client, dono, soro, lote_soro["id"], quantidade=5)
    _saida(client, dono, luva, lote_luva["id"], quantidade=1)

    r = client.get(f"{BASE}/resumo?dias=30", headers=auth(dono["token"]))
    assert r.status_code == 200
    dados = r.get_json()
    assert dados["movimentacoes_mes"] == 5
    assert [(c["nome"], c["quantidade"]) for c in dados["mais_consumidos"]] == [
        ("Soro Fisiológico", 5), ("Luva de Procedimento M", 3),
    ]


def test_clinicas_nao_enxergam_estoque_uma_da_outra(client, cenario):
    dono = cenario.dono()
    outro = cenario.dono("Outra Clínica")
    item = _item(client, dono)
    r = client.get(f"{BASE}/itens/{item['id']}", headers=auth(outro["token"]))
    assert r.status_code == 404
    assert client.get(f"{BASE}/itens", headers=auth(outro["token"])).get_json() == []


def test_permissao_estoque_pode_ser_revogada(client, cenario):
    dono = cenario.dono()
    recepcao = cenario.membro(dono, papel="Recepção")
    assert client.get(f"{BASE}/itens", headers=auth(recepcao["token"])).status_code == 200

    r = client.patch(f"/api/usuarios/{recepcao['id']}/permissoes", json={"permissoes": {"estoque": False}},
                     headers=auth(dono["token"]))
    assert r.status_code == 200, r.get_json()
    assert client.get(f"{BASE}/itens", headers=auth(recepcao["token"])).status_code == 403

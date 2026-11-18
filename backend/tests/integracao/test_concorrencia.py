"""Operações simultâneas reais (threads + PostgreSQL) em estoque e esterilização.

Antes da unificação o saldo era "lido e depois gravado" pela aplicação: duas
saídas simultâneas liam o mesmo saldo e uma atualização se perdia. Agora a
baixa é atômica (função SQL com UPDATE condicional) e estes testes provam que
nenhuma unidade é perdida, duplicada ou fica negativa.
"""

import threading
from datetime import date

import pytest

from apoio import auth, consultar

pytestmark = pytest.mark.integracao

HOJE = date.today().isoformat()
N_THREADS = 12


def _em_paralelo(app, n, funcao):
    """Roda funcao(client, i) em n threads que começam juntas. Devolve os status."""
    barreira = threading.Barrier(n)
    resultados = [None] * n
    erros = []

    def trabalho(i):
        cliente = app.test_client()
        try:
            barreira.wait()
            resultados[i] = funcao(cliente, i)
        except Exception as e:  # pragma: no cover - falha do próprio teste
            erros.append(e)

    threads = [threading.Thread(target=trabalho, args=(i,)) for i in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(30)
    assert not erros, erros
    return resultados


def _item_com_estoque(client, dono, quantidade):
    h = auth(dono["token"])
    forn = client.post("/api/estoque/fornecedores", headers=h, json={"nome": "F"}).get_json()
    item = client.post("/api/estoque/itens", headers=h, json={
        "nome": "Anestésico", "categoria": "Insumo", "unidade": "un", "estoque_minimo": 1}).get_json()
    if quantidade:
        r = client.post("/api/estoque/entradas", headers=h, json={
            "item_id": item["id"], "quantidade": quantidade, "lote": "L1", "validade": "2030-01-01",
            "fornecedor_id": forn["id"], "data": HOJE})
        assert r.status_code == 201, r.get_json()
        return item, forn, r.get_json()["lote"]
    return item, forn, None


@pytest.mark.estoque
def test_saidas_simultaneas_nao_perdem_nem_negativam_saldo(app, client, cenario):
    dono = cenario.dono()
    item, _, lote = _item_com_estoque(client, dono, 8)

    def saida(c, i):
        return c.post("/api/estoque/saidas", headers=auth(dono["token"]), json={
            "item_id": item["id"], "lote_id": lote["id"], "quantidade": 1,
            "motivo": "Uso em procedimento", "data": HOJE, "responsavel_id": dono["id"]}).status_code

    status = _em_paralelo(app, N_THREADS, saida)
    assert sorted(status) == [201] * 8 + [409] * (N_THREADS - 8), status
    (saldo,), = consultar("SELECT quantidade FROM lotes_estoque WHERE id = %s", [lote["id"]])
    assert saldo == 0
    (n_saidas,), = consultar("SELECT count(*) FROM movimentacoes_estoque WHERE tipo = 'Saída'")
    assert n_saidas == 8, "cada saída aceita tem exatamente uma movimentação"


@pytest.mark.estoque
def test_entradas_simultaneas_somam_tudo_no_mesmo_lote(app, client, cenario):
    dono = cenario.dono()
    item, forn, _ = _item_com_estoque(client, dono, 0)

    def entrada(c, i):
        return c.post("/api/estoque/entradas", headers=auth(dono["token"]), json={
            "item_id": item["id"], "quantidade": 2, "lote": "NOVO", "validade": "2031-06-30",
            "fornecedor_id": forn["id"], "data": HOJE}).status_code

    assert _em_paralelo(app, N_THREADS, entrada) == [201] * N_THREADS
    lotes = consultar("SELECT quantidade FROM lotes_estoque WHERE item_id = %s", [item["id"]])
    assert lotes == [(2 * N_THREADS,)], "nenhuma soma perdida e nenhum lote duplicado"
    (n,), = consultar("SELECT count(*) FROM movimentacoes_estoque WHERE item_id = %s", [item["id"]])
    assert n == N_THREADS


@pytest.mark.estoque
def test_entradas_e_saidas_misturadas_fecham_o_saldo(app, client, cenario):
    dono = cenario.dono()
    item, forn, lote = _item_com_estoque(client, dono, 6)

    def operacao(c, i):
        h = auth(dono["token"])
        if i % 2:
            return c.post("/api/estoque/entradas", headers=h, json={
                "item_id": item["id"], "quantidade": 1, "lote": "L1", "validade": "2030-01-01",
                "fornecedor_id": forn["id"], "data": HOJE}).status_code
        return c.post("/api/estoque/saidas", headers=h, json={
            "item_id": item["id"], "lote_id": lote["id"], "quantidade": 1,
            "motivo": "Uso em procedimento", "data": HOJE, "responsavel_id": dono["id"]}).status_code

    status = _em_paralelo(app, N_THREADS, operacao)
    assert all(s == 201 for s in status), status
    (saldo,), = consultar("SELECT quantidade FROM lotes_estoque WHERE id = %s", [lote["id"]])
    entradas = sum(1 for i in range(N_THREADS) if i % 2)
    saidas = N_THREADS - entradas
    assert saldo == 6 + entradas - saidas


@pytest.mark.esterilizacao
def test_ciclos_simultaneos_recebem_numeros_distintos(app, client, cenario):
    dono = cenario.dono()
    equip = client.post("/api/esterilizacao/equipamentos", headers=auth(dono["token"]),
                        json={"identificacao": "AUTO-01"}).get_json()

    def ciclo(c, i):
        r = c.post("/api/esterilizacao/ciclos", headers=auth(dono["token"]), json={
            "equipamento_id": equip["id"], "iniciado_em": f"{HOJE}T08:{i:02d}:00", "temperatura_c": 134,
            "pressao_kgf_cm2": 2.1, "tempo_exposicao_min": 7,
            "pacotes": [{"conteudo": f"Kit {i}", "validade_dias": 30}]})
        return r.status_code

    n = 5  # TENTATIVAS_NUMERACAO cobre até 5 disputas simultâneas pelo mesmo número
    assert _em_paralelo(app, n, ciclo) == [201] * n
    numeros = sorted(x for (x,) in consultar("SELECT numero_ciclo FROM ciclos_esterilizacao"))
    assert numeros == list(range(1, n + 1))
    codigos = [x for (x,) in consultar("SELECT codigo FROM pacotes_esterilizados")]
    assert len(codigos) == len(set(codigos)) == n


@pytest.mark.esterilizacao
def test_reprovacao_simultanea_nunca_termina_aprovada(app, client, cenario):
    """RNE-011 sob concorrência: aprovar e reprovar ao mesmo tempo nunca deixa o
    ciclo 'Aprovado' depois de reprovado, nem pacote disponível de ciclo reprovado."""
    dono = cenario.dono()
    h = auth(dono["token"])
    equip = client.post("/api/esterilizacao/equipamentos", headers=h, json={"identificacao": "AUTO-02"}).get_json()
    ciclo = client.post("/api/esterilizacao/ciclos", headers=h, json={
        "equipamento_id": equip["id"], "iniciado_em": f"{HOJE}T08:00:00", "temperatura_c": 134,
        "pressao_kgf_cm2": 2.1, "tempo_exposicao_min": 7, "indicador_quimico": "Aprovado",
        "pacotes": [{"conteudo": "Kit", "validade_dias": 30}]}).get_json()

    def indicador(c, i):
        valor = "Reprovado" if i == 0 else "Aprovado"
        return c.put(f"/api/esterilizacao/ciclos/{ciclo['id']}/indicadores", headers=h,
                     json={"indicador_biologico": valor}).status_code

    status = _em_paralelo(app, 6, indicador)
    assert status[0] == 200, "a reprovação sempre é registrada"
    (resultado,), = consultar("SELECT resultado FROM ciclos_esterilizacao WHERE id = %s", [ciclo["id"]])
    assert resultado == "Reprovado"
    estados = {e for (e,) in consultar("SELECT estado FROM pacotes_esterilizados WHERE ciclo_id = %s", [ciclo["id"]])}
    assert estados == {"Bloqueado"}

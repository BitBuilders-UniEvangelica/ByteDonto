"""RF-020 / RNE-011 / RNE-018 — ciclos de esterilização, indicadores e pacotes."""

from datetime import date, timedelta

from conftest import auth

BASE = "/api/esterilizacao"


def _equipamento(client, quem, identificacao="AC01"):
    r = client.post(f"{BASE}/equipamentos", json={"identificacao": identificacao, "fabricante": "Cristófoli"},
                    headers=auth(quem["token"]))
    assert r.status_code == 201, r.get_json()
    return r.get_json()


def _ciclo(client, quem, equipamento, **extra):
    corpo = {
        "equipamento_id": equipamento["id"],
        "iniciado_em": f"{date.today().isoformat()}T08:00:00",
        "temperatura_c": 134,
        "pressao_kgf_cm2": 2.1,
        "tempo_exposicao_min": 7,
        "pacotes": [{"conteudo": "Kit clínico (espelho, pinça, sonda)", "validade_dias": 30}],
    }
    corpo.update(extra)
    return client.post(f"{BASE}/ciclos", json=corpo, headers=auth(quem["token"]))


def _indicadores(client, quem, ciclo, **corpo):
    return client.put(f"{BASE}/ciclos/{ciclo['id']}/indicadores", json=corpo, headers=auth(quem["token"]))


def test_registra_ciclo_com_parametros_e_pacote_identificado(client, cenario):
    dono = cenario.dono()
    equipamento = _equipamento(client, dono)

    r = _ciclo(client, dono, equipamento)
    assert r.status_code == 201, r.get_json()
    ciclo = r.get_json()
    assert ciclo["numero_ciclo"] == 1
    assert float(ciclo["temperatura_c"]) == 134.0
    assert ciclo["resultado"] == "Pendente"
    assert ciclo["responsavel_id"] == dono["id"]

    pacote = ciclo["pacotes"][0]
    assert pacote["codigo"] == "AC01-C0001-P01"
    assert pacote["data_esterilizacao"] == date.today().isoformat()
    assert pacote["data_limite_uso"] == (date.today() + timedelta(days=30)).isoformat()
    assert pacote["metodo"] == "Vapor saturado sob pressão"
    assert pacote["estado"] == "Aguardando liberação"


def test_numero_do_ciclo_e_sequencial_por_equipamento(client, cenario):
    dono = cenario.dono()
    ac01, ac02 = _equipamento(client, dono, "AC01"), _equipamento(client, dono, "AC02")
    assert _ciclo(client, dono, ac01).get_json()["numero_ciclo"] == 1
    assert _ciclo(client, dono, ac01).get_json()["numero_ciclo"] == 2
    assert _ciclo(client, dono, ac02).get_json()["numero_ciclo"] == 1


def test_indicadores_aprovados_liberam_os_pacotes(client, cenario):
    dono = cenario.dono()
    ciclo = _ciclo(client, dono, _equipamento(client, dono)).get_json()

    r = _indicadores(client, dono, ciclo, indicador_quimico="Aprovado")
    assert r.get_json()["resultado"] == "Pendente", "falta o indicador biológico"

    r = _indicadores(client, dono, ciclo, indicador_biologico="Aprovado")
    assert r.status_code == 200
    assert r.get_json()["resultado"] == "Aprovado"
    assert [p["estado"] for p in r.get_json()["pacotes"]] == ["Disponível"]


def test_biologico_nao_realizado_com_quimico_aprovado_aprova(client, cenario):
    dono = cenario.dono()
    r = _ciclo(client, dono, _equipamento(client, dono),
               indicador_quimico="Aprovado", indicador_biologico="Não realizado")
    assert r.get_json()["resultado"] == "Aprovado"
    assert r.get_json()["pacotes"][0]["estado"] == "Disponível"


def test_indicador_reprovado_bloqueia_todos_os_pacotes_do_ciclo(client, cenario):
    """RNE-011: reprovou, todos os pacotes do ciclo ficam bloqueados."""
    dono = cenario.dono()
    ciclo = _ciclo(client, dono, _equipamento(client, dono), indicador_quimico="Aprovado", pacotes=[
        {"conteudo": "Kit clínico", "validade_dias": 30},
        {"conteudo": "Kit cirúrgico", "validade_dias": 30},
    ]).get_json()

    r = _indicadores(client, dono, ciclo, indicador_biologico="Reprovado")
    assert r.status_code == 200
    assert r.get_json()["resultado"] == "Reprovado"
    assert [p["estado"] for p in r.get_json()["pacotes"]] == ["Bloqueado", "Bloqueado"]

    disponiveis = client.get(f"{BASE}/pacotes?disponiveis=1", headers=auth(dono["token"])).get_json()
    assert disponiveis == []


def test_ciclo_aprovado_que_depois_reprova_bloqueia_pacotes_ja_liberados(client, cenario):
    dono = cenario.dono()
    ciclo = _ciclo(client, dono, _equipamento(client, dono),
                   indicador_quimico="Aprovado", indicador_biologico="Não realizado").get_json()
    assert ciclo["pacotes"][0]["estado"] == "Disponível"

    r = _indicadores(client, dono, ciclo, indicador_biologico="Reprovado")
    assert r.get_json()["pacotes"][0]["estado"] == "Bloqueado"


def test_ciclo_reprovado_nao_pode_ser_reaprovado(client, cenario):
    dono = cenario.dono()
    ciclo = _ciclo(client, dono, _equipamento(client, dono), indicador_quimico="Reprovado").get_json()
    assert ciclo["pacotes"][0]["estado"] == "Bloqueado"

    assert _indicadores(client, dono, ciclo, indicador_quimico="Aprovado").status_code == 409
    r = client.post(f"{BASE}/ciclos/{ciclo['id']}/pacotes",
                    json={"pacotes": [{"conteudo": "Kit", "validade_dias": 30}]}, headers=auth(dono["token"]))
    assert r.status_code == 409


def test_pacote_com_data_limite_vencida_aparece_como_vencido(client, cenario):
    dono = cenario.dono()
    ontem = date.today() - timedelta(days=1)
    r = _ciclo(client, dono, _equipamento(client, dono),
               iniciado_em=f"{(ontem - timedelta(days=10)).isoformat()}T08:00:00",
               indicador_quimico="Aprovado", indicador_biologico="Aprovado",
               pacotes=[{"conteudo": "Kit clínico", "data_limite_uso": ontem.isoformat()}])
    assert r.get_json()["pacotes"][0]["estado"] == "Vencido"

    assert client.get(f"{BASE}/pacotes?disponiveis=1", headers=auth(dono["token"])).get_json() == []
    vencidos = client.get(f"{BASE}/pacotes?estado=Vencido", headers=auth(dono["token"])).get_json()
    assert len(vencidos) == 1


def test_adiciona_pacotes_depois_com_numeracao_continua(client, cenario):
    dono = cenario.dono()
    ciclo = _ciclo(client, dono, _equipamento(client, dono)).get_json()
    r = client.post(f"{BASE}/ciclos/{ciclo['id']}/pacotes",
                    json={"pacotes": [{"conteudo": "Brocas", "validade_dias": 15}]}, headers=auth(dono["token"]))
    assert r.status_code == 201
    assert r.get_json()[0]["codigo"] == "AC01-C0001-P02"


def test_valida_parametros_e_validade(client, cenario):
    dono = cenario.dono()
    equipamento = _equipamento(client, dono)
    assert _ciclo(client, dono, equipamento, temperatura_c=50).status_code == 400
    assert _ciclo(client, dono, equipamento, tempo_exposicao_min=0).status_code == 400
    assert _ciclo(client, dono, equipamento, indicador_quimico="Talvez").status_code == 400
    assert _ciclo(client, dono, equipamento, pacotes=[{"conteudo": "Kit"}]).status_code == 400
    assert _ciclo(client, dono, equipamento, pacotes=[{"validade_dias": 30}]).status_code == 400


def test_equipamento_inativo_nao_registra_ciclo_e_nao_ha_exclusao(client, cenario):
    """RNE-018: equipamento é inativado, nunca apagado."""
    dono = cenario.dono()
    equipamento = _equipamento(client, dono)
    r = client.put(f"{BASE}/equipamentos/{equipamento['id']}", json={"ativo": False},
                   headers=auth(dono["token"]))
    assert r.status_code == 200 and r.get_json()["ativo"] is False

    assert _ciclo(client, dono, equipamento).status_code == 400
    assert client.delete(f"{BASE}/equipamentos/{equipamento['id']}",
                         headers=auth(dono["token"])).status_code == 405

    ativos = client.get(f"{BASE}/equipamentos", headers=auth(dono["token"])).get_json()
    todos = client.get(f"{BASE}/equipamentos?todos=1", headers=auth(dono["token"])).get_json()
    assert ativos == [] and len(todos) == 1


def test_identificacao_de_equipamento_nao_repete_na_clinica(client, cenario):
    dono = cenario.dono()
    _equipamento(client, dono, "AC01")
    r = client.post(f"{BASE}/equipamentos", json={"identificacao": "AC01"}, headers=auth(dono["token"]))
    assert r.status_code == 409


def test_permissoes_e_isolamento_entre_clinicas(client, cenario):
    dono = cenario.dono("Dono A")
    especialista = cenario.membro(dono, "Especialista")
    recepcao = cenario.membro(dono, "Recepção")
    equipamento = _equipamento(client, dono)

    assert _ciclo(client, especialista, equipamento).status_code == 201
    assert client.get(f"{BASE}/ciclos", headers=auth(recepcao["token"])).status_code == 403

    outro_dono = cenario.dono("Dono B")
    assert _ciclo(client, outro_dono, equipamento).status_code == 404
    assert client.get(f"{BASE}/ciclos", headers=auth(outro_dono["token"])).get_json() == []

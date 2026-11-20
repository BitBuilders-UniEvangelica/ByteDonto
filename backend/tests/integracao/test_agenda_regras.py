"""Regras da agenda (Fase 3) contra PostgreSQL real: sobreposição, ciclo de
vida, auditoria, fuso, concorrência e consistência após falha de transação."""

import threading
import time

import psycopg
import pytest

from apoio import TEST_DATABASE_URL, auth, consultar, executar, foto_do_banco

pytestmark = pytest.mark.agenda

DIA = "2026-11-10"


@pytest.fixture
def agenda(client, cenario):
    dono = cenario.dono()
    recep = cenario.membro(dono, "Recepção")
    d1 = cenario.membro(dono, "Especialista")
    d2 = cenario.membro(dono, "Especialista")
    p1, p2, p3 = cenario.paciente(dono), cenario.paciente(dono), cenario.paciente(dono)
    return dict(dono=dono, recep=recep, d1=d1, d2=d2, p1=p1, p2=p2, p3=p3)


def marcar(client, a, paciente, dentista, hora, duracao=30, quem="recep", **extra):
    corpo = {"paciente_id": paciente["id"], "data_agendada": f"{DIA}T{hora}:00", "duracao_minutos": duracao}
    if dentista is not None:
        corpo["dentista_id"] = dentista["id"]
    corpo.update(extra)
    return client.post("/api/consultas/", headers=auth(a[quem]["token"]), json=corpo)


def alterar(client, a, consulta_id, quem="recep", **corpo):
    return client.put(f"/api/consultas/{consulta_id}", headers=auth(a[quem]["token"]), json=corpo)


def n_atendimentos():
    return consultar("SELECT count(*) FROM atendimentos")[0][0]


# ---- sobreposição -----------------------------------------------------------

@pytest.mark.parametrize("hora,duracao", [
    ("09:00", 30),   # mesmo horário
    ("09:15", 30),   # começa no meio
    ("08:45", 30),   # termina no meio
    ("08:30", 120),  # engloba
    ("09:10", 10),   # contido
])
def test_sobreposicao_do_mesmo_profissional_e_recusada(client, agenda, hora, duracao):
    assert marcar(client, agenda, agenda["p1"], agenda["d1"], "09:00").status_code == 201
    antes = foto_do_banco()
    r = marcar(client, agenda, agenda["p2"], agenda["d1"], hora, duracao)
    assert r.status_code == 409, r.get_json()
    corpo = r.get_json()
    assert corpo["codigo"] == "conflito_horario"
    assert "10/11/2026 09:00 às 09:30" in corpo["error"]
    assert foto_do_banco() == antes


def test_horarios_consecutivos_sao_permitidos(client, agenda):
    assert marcar(client, agenda, agenda["p1"], agenda["d1"], "09:00").status_code == 201
    assert marcar(client, agenda, agenda["p2"], agenda["d1"], "09:30").status_code == 201
    assert marcar(client, agenda, agenda["p3"], agenda["d1"], "08:30").status_code == 201
    assert n_atendimentos() == 3


def test_profissionais_diferentes_podem_atender_no_mesmo_horario(client, agenda):
    assert marcar(client, agenda, agenda["p1"], agenda["d1"], "09:00").status_code == 201
    assert marcar(client, agenda, agenda["p2"], agenda["d2"], "09:00").status_code == 201


def test_duracao_e_considerada(client, agenda):
    assert marcar(client, agenda, agenda["p1"], agenda["d1"], "09:00", duracao=90).status_code == 201
    assert marcar(client, agenda, agenda["p2"], agenda["d1"], "10:00").status_code == 409
    assert marcar(client, agenda, agenda["p2"], agenda["d1"], "10:30").status_code == 201


def test_sem_duracao_usa_30_minutos(client, agenda):
    corpo = {"paciente_id": agenda["p1"]["id"], "dentista_id": agenda["d1"]["id"], "data_agendada": f"{DIA}T09:00:00"}
    assert client.post("/api/consultas/", headers=auth(agenda["recep"]["token"]), json=corpo).status_code == 201
    assert marcar(client, agenda, agenda["p2"], agenda["d1"], "09:29", duracao=5).status_code == 409
    assert marcar(client, agenda, agenda["p2"], agenda["d1"], "09:30").status_code == 201


@pytest.mark.parametrize("como", ["delete", "put"])
def test_cancelado_libera_o_horario(client, agenda, como):
    c = marcar(client, agenda, agenda["p1"], agenda["d1"], "09:00").get_json()
    assert marcar(client, agenda, agenda["p2"], agenda["d1"], "09:00").status_code == 409
    if como == "delete":
        assert client.delete(f"/api/consultas/{c['id']}", headers=auth(agenda["recep"]["token"])).status_code == 200
    else:
        assert alterar(client, agenda, c["id"], status="Cancelado").status_code == 200
    assert marcar(client, agenda, agenda["p2"], agenda["d1"], "09:00").status_code == 201


def test_atendimento_sem_profissional_nao_bloqueia_horario(client, agenda):
    """Sem profissional não há agenda a ocupar (comportamento atual preservado)."""
    assert marcar(client, agenda, agenda["p1"], None, "09:00").status_code == 201
    assert marcar(client, agenda, agenda["p2"], None, "09:00").status_code == 201


# ---- edição / reagendamento ---------------------------------------------------

def test_edicao_que_cria_conflito_e_recusada(client, agenda):
    a = marcar(client, agenda, agenda["p1"], agenda["d1"], "09:00").get_json()
    b = marcar(client, agenda, agenda["p2"], agenda["d1"], "10:00").get_json()
    c = marcar(client, agenda, agenda["p3"], agenda["d2"], "09:00").get_json()
    antes = foto_do_banco()
    assert alterar(client, agenda, b["id"], data_agendada=f"{DIA}T09:15:00").status_code == 409   # horário
    assert alterar(client, agenda, a["id"], duracao_minutos=90).status_code == 409                # duração
    assert alterar(client, agenda, c["id"], dentista_id=agenda["d1"]["id"]).status_code == 409    # profissional
    assert foto_do_banco() == antes


def test_reagendamento_libera_o_horario_antigo(client, agenda):
    a = marcar(client, agenda, agenda["p1"], agenda["d1"], "09:00").get_json()
    r = alterar(client, agenda, a["id"], data_agendada=f"{DIA}T14:00:00", duracao_minutos=60)
    assert r.status_code == 200, r.get_json()
    assert r.get_json()["data_agendada"] == f"{DIA}T14:00:00"
    assert marcar(client, agenda, agenda["p2"], agenda["d1"], "09:00").status_code == 201
    assert marcar(client, agenda, agenda["p3"], agenda["d1"], "14:30").status_code == 409


def test_trocar_profissional_para_um_livre(client, agenda):
    a = marcar(client, agenda, agenda["p1"], agenda["d1"], "09:00").get_json()
    r = alterar(client, agenda, a["id"], dentista_id=agenda["d2"]["id"])
    assert r.status_code == 200, r.get_json()
    assert marcar(client, agenda, agenda["p2"], agenda["d1"], "09:00").status_code == 201


def test_editar_o_proprio_atendimento_sem_mudar_horario_nao_conflita_consigo(client, agenda):
    a = marcar(client, agenda, agenda["p1"], agenda["d1"], "09:00").get_json()
    assert alterar(client, agenda, a["id"], data_agendada=f"{DIA}T09:00:00", cadeira="2").status_code == 200
    assert alterar(client, agenda, a["id"], duracao_minutos=20).status_code == 200


@pytest.mark.parametrize("duracao", [0, -5, 4, 481, "abc", 30.5, True, ""])
def test_duracao_invalida(client, agenda, duracao):
    r = marcar(client, agenda, agenda["p1"], agenda["d1"], "09:00", duracao=duracao)
    if duracao == "":
        assert r.status_code in (201, 400)  # "" = não informado -> padrão 30
        return
    assert r.status_code == 400, r.get_json()
    a = marcar(client, agenda, agenda["p1"], agenda["d1"], "11:00").get_json()
    assert alterar(client, agenda, a["id"], duracao_minutos=duracao).status_code == 400


def test_duracao_nula_na_edicao_e_recusada(client, agenda):
    a = marcar(client, agenda, agenda["p1"], agenda["d1"], "09:00").get_json()
    assert alterar(client, agenda, a["id"], duracao_minutos=None).status_code == 400


@pytest.mark.parametrize("valor", [None, "", "amanhã", "2026-13-40T09:00:00", "10/11/2026 09:00", 123])
def test_data_invalida_ou_ausente(client, agenda, valor):
    corpo = {"paciente_id": agenda["p1"]["id"], "dentista_id": agenda["d1"]["id"], "data_agendada": valor}
    r = client.post("/api/consultas/", headers=auth(agenda["recep"]["token"]), json=corpo)
    assert r.status_code == 400, r.get_json()


def test_dados_obrigatorios_e_corpo_invalido(client, agenda):
    h = auth(agenda["recep"]["token"])
    assert client.post("/api/consultas/", headers=h, json={"data_agendada": f"{DIA}T09:00"}).status_code == 400
    assert client.post("/api/consultas/", headers=h, json=["x"]).status_code == 400
    assert client.post("/api/consultas/", headers=h, json={**{"paciente_id": agenda["p1"]["id"]},
                                                          "data_agendada": f"{DIA}T09:00", "status": "Inventado"}).status_code == 400


# ---- profissional e paciente da clínica certa ---------------------------------

def test_profissional_precisa_ser_clinico_ativo_e_da_clinica(client, cenario, agenda):
    outro_dono = cenario.dono("Outra")
    dentista_fora = cenario.membro(outro_dono, "Especialista")
    assert marcar(client, agenda, agenda["p1"], dentista_fora, "09:00").status_code == 404
    assert marcar(client, agenda, agenda["p1"], agenda["recep"], "09:00").status_code == 400
    assert marcar(client, agenda, agenda["p1"], agenda["dono"], "09:00").status_code == 201  # Dono também atende
    r = client.put(f"/api/usuarios/{agenda['d2']['id']}", headers=auth(agenda["dono"]["token"]), json={"ativo": False})
    assert r.status_code == 200
    assert marcar(client, agenda, agenda["p2"], agenda["d2"], "10:00").status_code == 400
    a = marcar(client, agenda, agenda["p3"], agenda["d1"], "11:00").get_json()
    assert alterar(client, agenda, a["id"], dentista_id=dentista_fora["id"]).status_code == 404
    paciente_fora = cenario.paciente(outro_dono)
    assert marcar(client, agenda, paciente_fora, agenda["d1"], "15:00").status_code == 404


def test_paciente_do_atendimento_nao_muda(client, agenda):
    a = marcar(client, agenda, agenda["p1"], agenda["d1"], "09:00").get_json()
    r = alterar(client, agenda, a["id"], paciente_id=agenda["p2"]["id"], cadeira="1")
    assert r.status_code == 400
    with pytest.raises(psycopg.errors.RaiseException, match="ATENDIMENTO_IMUTAVEL"):
        executar("UPDATE atendimentos SET paciente_id = %s WHERE id = %s", [agenda["p2"]["id"], a["id"]])
    assert consultar("SELECT paciente_id::text FROM atendimentos WHERE id = %s", [a["id"]])[0][0] == agenda["p1"]["id"]


# ---- ciclo de vida -------------------------------------------------------------

@pytest.mark.parametrize("caminho,ok", [
    (["Aguardando", "Finalizado"], True),
    (["Aguardando", "Cancelado"], True),
    (["Aguardando", "Faltou"], True),
    (["Faltou"], True),
    (["Finalizado"], True),
    (["Finalizado", "Agendado"], False),
    (["Finalizado", "Cancelado"], False),
    (["Cancelado", "Agendado"], False),
    (["Cancelado", "Aguardando"], False),
    (["Faltou", "Aguardando"], False),
    (["Aguardando", "Agendado"], False),
])
def test_transicoes_de_status(client, agenda, caminho, ok):
    a = marcar(client, agenda, agenda["p1"], agenda["d1"], "09:00").get_json()
    *antes, ultimo = caminho
    for s in antes:
        assert alterar(client, agenda, a["id"], quem="dono", status=s).status_code == 200
    r = alterar(client, agenda, a["id"], quem="dono", status=ultimo)
    assert r.status_code == (200 if ok else 409), r.get_json()
    if not ok:
        assert r.get_json()["codigo"] == "transicao_invalida"
        assert consultar("SELECT status FROM atendimentos WHERE id = %s", [a["id"]])[0][0] == antes[-1]


def test_mesmo_status_repetido_e_idempotente(client, agenda):
    a = marcar(client, agenda, agenda["p1"], agenda["d1"], "09:00").get_json()
    assert alterar(client, agenda, a["id"], status="Aguardando").status_code == 200
    assert alterar(client, agenda, a["id"], status="Aguardando").status_code == 200


def test_atendimento_encerrado_nao_e_remarcado_mas_aceita_evolucao(client, agenda):
    a = marcar(client, agenda, agenda["p1"], agenda["d1"], "09:00").get_json()
    assert alterar(client, agenda, a["id"], quem="d1", status="Finalizado", evolucao_clinica="ok").status_code == 200
    r = alterar(client, agenda, a["id"], quem="dono", data_agendada=f"{DIA}T15:00:00")
    assert r.status_code == 409 and r.get_json()["codigo"] == "atendimento_encerrado"
    assert alterar(client, agenda, a["id"], quem="d1", evolucao_clinica="complemento").status_code == 200
    # Finalizado continua ocupando o horário (só Cancelado libera)
    assert marcar(client, agenda, agenda["p2"], agenda["d1"], "09:00").status_code == 409


def test_cancelamento_repetido_e_idempotente_e_encerrado_nao_cancela(client, agenda):
    h = auth(agenda["recep"]["token"])
    a = marcar(client, agenda, agenda["p1"], agenda["d1"], "09:00").get_json()
    assert client.delete(f"/api/consultas/{a['id']}", headers=h).status_code == 200
    assert client.delete(f"/api/consultas/{a['id']}", headers=h).status_code == 200
    n_audit = consultar("SELECT count(*) FROM auditoria_prontuario WHERE registro_id = %s AND acao = 'UPDATE'", [a["id"]])[0][0]
    assert n_audit == 1, "cancelamento repetido não gera nova auditoria"
    b = marcar(client, agenda, agenda["p2"], agenda["d1"], "10:00").get_json()
    assert alterar(client, agenda, b["id"], quem="dono", status="Finalizado").status_code == 200
    assert client.delete(f"/api/consultas/{b['id']}", headers=h).status_code == 409


def test_requisicao_repetida_nao_duplica_agendamento(client, agenda):
    """Duplo clique sem profissional: o mesmo paciente no mesmo início é recusado."""
    assert marcar(client, agenda, agenda["p1"], None, "09:00").status_code == 201
    r = marcar(client, agenda, agenda["p1"], None, "09:00")
    assert r.status_code == 409 and r.get_json()["codigo"] == "agendamento_duplicado"
    assert n_atendimentos() == 1


def test_historico_registrado_na_auditoria(client, agenda):
    a = marcar(client, agenda, agenda["p1"], agenda["d1"], "09:00").get_json()
    alterar(client, agenda, a["id"], data_agendada=f"{DIA}T11:00:00")
    alterar(client, agenda, a["id"], status="Aguardando")
    linhas = consultar("SELECT acao, campos FROM auditoria_prontuario WHERE registro_id = %s ORDER BY id", [a["id"]])
    assert [l[0] for l in linhas] == ["INSERT", "UPDATE", "UPDATE"]
    remarcacao = linhas[1][1]["data_agendada"]
    assert remarcacao["antes"].startswith(f"{DIA}T09:00") and remarcacao["depois"].startswith(f"{DIA}T11:00")
    assert linhas[2][1]["status"] == {"antes": "Agendado", "depois": "Aguardando"}


# ---- fuso horário --------------------------------------------------------------

def test_horario_sem_fuso_e_devolvido_igual_e_com_fuso_e_convertido(client, agenda):
    r = marcar(client, agenda, agenda["p1"], agenda["d1"], "09:00")
    assert r.get_json()["data_agendada"] == f"{DIA}T09:00:00"  # sem "+00:00": todas as telas leem 09:00
    # 12:00 UTC = 09:00 em São Paulo -> mesmo horário de parede -> conflito
    corpo = {"paciente_id": agenda["p2"]["id"], "dentista_id": agenda["d1"]["id"], "data_agendada": f"{DIA}T12:00:00Z"}
    assert client.post("/api/consultas/", headers=auth(agenda["recep"]["token"]), json=corpo).status_code == 409
    corpo["data_agendada"] = f"{DIA}T10:00:00-03:00"
    r = client.post("/api/consultas/", headers=auth(agenda["recep"]["token"]), json=corpo)
    assert r.status_code == 201 and r.get_json()["data_agendada"] == f"{DIA}T10:00:00"
    lista = client.get("/api/consultas/", headers=auth(agenda["d1"]["token"])).get_json()
    assert sorted(c["data_agendada"] for c in lista) == [f"{DIA}T09:00:00", f"{DIA}T10:00:00"]


def test_metricas_de_hoje_usam_o_dia_da_clinica(client, agenda):
    from app.horarios import hoje
    corpo = {"paciente_id": agenda["p1"]["id"], "dentista_id": agenda["d1"]["id"],
             "data_agendada": f"{hoje().isoformat()}T23:30:00"}
    assert client.post("/api/consultas/", headers=auth(agenda["recep"]["token"]), json=corpo).status_code == 201
    m = client.get("/api/dashboard/metricas", headers=auth(agenda["dono"]["token"])).get_json()
    assert m["consultas_hoje"] == 1


# ---- dados antigos -------------------------------------------------------------

def test_sobreposicoes_antigas_nao_travam_edicoes_que_nao_mexem_no_horario(client, agenda):
    """Produção pode ter sobreposições criadas antes da regra. Elas não impedem
    check-in, evolução ou finalização — só gravações que mudem o horário."""
    ids = []
    with psycopg.connect(TEST_DATABASE_URL, autocommit=True) as conn:
        conn.execute("SET session_replication_role = replica")  # simula dado legado (sem trigger)
        conn.execute("SET TimeZone = 'UTC'")  # sessões da API/PostgREST gravam em UTC
        for p in (agenda["p1"], agenda["p2"]):
            ids.append(conn.execute(
                "INSERT INTO atendimentos (clinica_id, paciente_id, dentista_id, data_agendada, duracao_minutos) "
                "VALUES (%s, %s, %s, %s, 30) RETURNING id::text",
                [agenda["dono"]["clinica_id"], p["id"], agenda["d1"]["id"], f"{DIA}T09:00:00"]).fetchone()[0])
    assert alterar(client, agenda, ids[0], status="Aguardando").status_code == 200
    assert alterar(client, agenda, ids[0], quem="d1", status="Finalizado", evolucao_clinica="ok").status_code == 200
    assert alterar(client, agenda, ids[1], data_agendada=f"{DIA}T09:10:00").status_code == 409


# ---- concorrência e transações --------------------------------------------------

def _paralelo(app, n, funcao):
    barreira = threading.Barrier(n)
    resultados = [None] * n

    def trabalho(i):
        c = app.test_client()
        barreira.wait()
        resultados[i] = funcao(c, i)

    threads = [threading.Thread(target=trabalho, args=(i,)) for i in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(30)
    return resultados


def test_requisicoes_simultaneas_para_o_mesmo_horario(app, cenario):
    dono = cenario.dono()
    dentista = cenario.membro(dono, "Especialista")
    pacientes = [cenario.paciente(dono) for _ in range(8)]

    def reservar(c, i):
        return c.post("/api/consultas/", headers=auth(dono["token"]), json={
            "paciente_id": pacientes[i]["id"], "dentista_id": dentista["id"],
            "data_agendada": f"{DIA}T09:{i * 2:02d}:00", "duracao_minutos": 30}).status_code

    status = _paralelo(app, 8, reservar)
    assert sorted(status) == [201] + [409] * 7, status
    assert consultar("SELECT count(*) FROM atendimentos")[0][0] == 1


def test_reagendamentos_simultaneos_para_o_mesmo_horario_livre(app, client, agenda):
    ids = [marcar(client, agenda, p, agenda["d1"], hora).get_json()["id"]
           for p, hora in ((agenda["p1"], "08:00"), (agenda["p2"], "10:00"), (agenda["p3"], "12:00"))]

    def mover(c, i):
        return c.put(f"/api/consultas/{ids[i]}", headers=auth(agenda["recep"]["token"]),
                     json={"data_agendada": f"{DIA}T15:00:00"}).status_code

    status = _paralelo(app, 3, mover)
    assert sorted(status) == [200, 409, 409], status
    (n,), = consultar("SELECT count(*) FROM atendimentos WHERE data_agendada = %s", [f"{DIA}T15:00:00+00"])
    assert n == 1


def test_transacao_desfeita_libera_o_horario_e_nao_deixa_rastro(client, agenda):
    """Uma transação concorrente segura o horário (lock) e falha: a API espera,
    vê o rollback e reserva normalmente. Nada da transação falha permanece."""
    resultado = {}
    conn = psycopg.connect(TEST_DATABASE_URL)
    conn.execute("SET TimeZone = 'UTC'")
    try:
        conn.execute(
            "INSERT INTO atendimentos (clinica_id, paciente_id, dentista_id, data_agendada) VALUES (%s, %s, %s, %s)",
            [agenda["dono"]["clinica_id"], agenda["p1"]["id"], agenda["d1"]["id"], f"{DIA}T09:00:00"])

        def reservar():
            resultado["r"] = marcar(client, agenda, agenda["p2"], agenda["d1"], "09:00")

        t = threading.Thread(target=reservar)
        t.start()
        time.sleep(0.5)
        assert t.is_alive(), "a API deveria esperar o lock da transação concorrente"
        conn.rollback()  # a transação concorrente falha
        t.join(10)
    finally:
        conn.close()
    assert resultado["r"].status_code == 201, resultado["r"].get_json()
    assert consultar("SELECT paciente_id::text FROM atendimentos") == [(agenda["p2"]["id"],)]


def test_falha_no_banco_nao_deixa_agendamento_nem_auditoria(client, agenda):
    assert marcar(client, agenda, agenda["p1"], agenda["d1"], "09:00").status_code == 201
    audit_antes = consultar("SELECT count(*) FROM auditoria_prontuario")[0][0]
    assert marcar(client, agenda, agenda["p2"], agenda["d1"], "09:10").status_code == 409
    assert consultar("SELECT count(*) FROM auditoria_prontuario")[0][0] == audit_antes
    # o lock da transação que falhou foi liberado: a próxima reserva passa na hora
    inicio = time.monotonic()
    assert marcar(client, agenda, agenda["p2"], agenda["d1"], "09:30").status_code == 201
    assert time.monotonic() - inicio < 2

"""Cache das leituras frequentes (app/cache.py).

Garante: (1) a segunda leitura vem do cache; (2) toda escrita invalida;
(3) a chave separa clínica E usuário — nunca vaza dado entre clínicas;
(4) prontuário, documentos e URLs assinadas não entram no cache.
"""

import pytest

from apoio import Cenario, auth
from app import cache
from config import Config

pytestmark = [pytest.mark.rotas, pytest.mark.isolamento]


@pytest.fixture(autouse=True)
def ttl_curto(monkeypatch):
    monkeypatch.setattr(Config, "CACHE_TTL_SECONDS", 60)
    cache.limpar_tudo()
    yield
    cache.limpar_tudo()


def _get(client, url, quem):
    r = client.get(url, headers=auth(quem["token"]))
    return r, r.get_json()


def test_segunda_leitura_vem_do_cache(client, cenario):
    dono = cenario.dono()
    cenario.paciente(dono)
    r1, d1 = _get(client, "/api/pacientes/", dono)
    r2, d2 = _get(client, "/api/pacientes/", dono)
    assert r1.headers["X-Cache"] == "MISS" and r2.headers["X-Cache"] == "HIT"
    assert d1 == d2 and d2["total"] == 1


def test_parametros_diferentes_sao_entradas_diferentes(client, cenario):
    dono = cenario.dono()
    cenario.paciente(dono, nome="Ana Souza")
    cenario.paciente(dono, nome="Bruno Lima")
    _get(client, "/api/pacientes/?busca=Ana", dono)
    r, d = _get(client, "/api/pacientes/?busca=Bruno", dono)
    assert r.headers["X-Cache"] == "MISS" and [p["nome"] for p in d["items"]] == ["Bruno Lima"]


@pytest.mark.parametrize("escrita", ["criar", "editar", "excluir"])
def test_escrita_de_paciente_invalida(client, cenario, escrita):
    dono = cenario.dono()
    pac = cenario.paciente(dono, nome="Antes")
    h = auth(dono["token"])
    _get(client, "/api/pacientes/", dono)
    if escrita == "criar":
        cenario.paciente(dono)
        esperado = 2
    elif escrita == "editar":
        assert client.put(f"/api/pacientes/{pac['id']}", headers=h, json={"nome": "Depois"}).status_code == 200
        esperado = 1
    else:
        assert client.delete(f"/api/pacientes/{pac['id']}", headers=h).status_code == 200
        esperado = 0
    r, d = _get(client, "/api/pacientes/", dono)
    assert r.headers["X-Cache"] == "MISS" and d["total"] == esperado
    if escrita == "editar":
        assert d["items"][0]["nome"] == "Depois"


def test_nova_consulta_invalida_lista_de_pacientes(client, cenario):
    dono = cenario.dono()
    pac = cenario.paciente(dono)
    _, antes = _get(client, "/api/pacientes/", dono)
    assert antes["items"][0]["ultima_consulta"] is None
    r = client.post("/api/consultas/", headers=auth(dono["token"]), json={
        "paciente_id": pac["id"], "dentista_id": dono["id"], "data_agendada": "2026-06-01T08:00:00"})
    assert r.status_code == 201
    _, depois = _get(client, "/api/pacientes/", dono)
    assert depois["items"][0]["ultima_consulta"] == "2026-06-01T08:00:00"


def test_cache_nunca_vaza_entre_clinicas(client, cenario):
    dono_a, dono_b = cenario.dono("A"), cenario.dono("B")
    cenario.paciente(dono_a, nome="Paciente Sigiloso")
    # A clínica A aquece o cache com exatamente a mesma URL que B vai pedir.
    for url in ("/api/pacientes/", "/api/pacientes/opcoes", "/api/usuarios/", "/api/financeiro/resumo"):
        _get(client, url, dono_a)
        r, d = _get(client, url, dono_b)
        assert r.headers["X-Cache"] == "MISS", url
        assert "Paciente Sigiloso" not in r.get_data(as_text=True), url
        assert dono_a["id"] not in r.get_data(as_text=True), url


def test_cache_separa_usuarios_da_mesma_clinica(client, cenario):
    dono = cenario.dono()
    recep = cenario.membro(dono, "Recepção")
    _, do_dono = _get(client, "/api/usuarios/", dono)
    r, da_recep = _get(client, "/api/usuarios/", recep)
    assert r.headers["X-Cache"] == "MISS"
    assert "permissoes" in do_dono[0]
    assert all("permissoes" not in m and "percentual_repasse" not in m for m in da_recep)


def test_permissao_e_conferida_mesmo_com_cache_quente(client, cenario):
    dono = cenario.dono()
    recep = cenario.membro(dono, "Recepção")
    assert _get(client, "/api/pacientes/", recep)[0].status_code == 200
    assert _get(client, "/api/pacientes/", recep)[0].headers["X-Cache"] == "HIT"
    r = client.patch(f"/api/usuarios/{recep['id']}/permissoes", headers=auth(dono["token"]),
                     json={"permissoes": {"ver_pacientes": False}})
    assert r.status_code == 200
    assert _get(client, "/api/pacientes/", recep)[0].status_code == 403


def test_prontuario_documentos_e_links_nao_entram_no_cache(client, cenario):
    dono = cenario.dono()
    pac = cenario.paciente(dono)
    for url in (f"/api/pacientes/{pac['id']}", f"/api/planos/?paciente_id={pac['id']}",
                f"/api/imagens/?paciente_id={pac['id']}", f"/api/consultas/?paciente_id={pac['id']}"):
        for _ in range(2):
            r = client.get(url, headers=auth(dono["token"]))
            assert r.status_code == 200, url
            assert "X-Cache" not in r.headers, url
    assert cache.estatisticas()["entradas"] == 0


def test_agenda_do_dia_so_em_cache_para_quem_nao_ve_prontuario(client, cenario):
    dono = cenario.dono()
    recep = cenario.membro(dono, "Recepção")
    url = "/api/consultas/?data_inicio=2026-06-01&data_fim=2026-06-01"
    assert _get(client, url, recep)[0].headers["X-Cache"] == "MISS"
    assert _get(client, url, recep)[0].headers["X-Cache"] == "HIT"
    assert "X-Cache" not in _get(client, url, dono)[0].headers  # Dono vê evolução clínica


def test_ttl_expira(client, cenario, monkeypatch):
    dono = cenario.dono()
    _get(client, "/api/usuarios/", dono)
    relogio = [cache.time.monotonic() + 61]
    monkeypatch.setattr(cache.time, "monotonic", lambda: relogio[0])
    assert _get(client, "/api/usuarios/", dono)[0].headers["X-Cache"] == "MISS"


def test_ttl_zero_desliga(client, cenario, monkeypatch):
    monkeypatch.setattr(Config, "CACHE_TTL_SECONDS", 0)
    dono = cenario.dono()
    for _ in range(2):
        assert _get(client, "/api/usuarios/", dono)[0].headers["X-Cache"] == "BYPASS"

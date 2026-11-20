"""Convenção de horário da agenda (app/horarios.py)."""

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from app import horarios


@pytest.mark.parametrize("entrada,esperado", [
    ("2026-11-10T09:00:00", "2026-11-10T09:00:00"),     # sem fuso: horário de parede
    ("2026-11-10T09:00", "2026-11-10T09:00:00"),
    ("2026-11-10T09:00:00.123456", "2026-11-10T09:00:00"),
    ("2026-11-10T12:00:00Z", "2026-11-10T09:00:00"),    # UTC -> São Paulo (-03:00)
    ("2026-11-10T12:00:00+00:00", "2026-11-10T09:00:00"),
    ("2026-11-10T09:00:00-03:00", "2026-11-10T09:00:00"),
    ("2026-11-10T23:30:00-02:00", "2026-11-10T22:30:00"),
])
def test_normalizar_entrada(entrada, esperado):
    assert horarios.normalizar_entrada(entrada) == esperado


@pytest.mark.parametrize("entrada", [None, "", "  ", "amanhã", "2026-02-30T09:00", "10/11/2026 09:00"])
def test_entrada_invalida(entrada):
    with pytest.raises(ValueError):
        horarios.normalizar_entrada(entrada)


@pytest.mark.parametrize("valor,esperado", [
    ("2026-11-10T09:00:00+00:00", "2026-11-10T09:00:00"),   # como o banco devolve
    ("2026-11-10T09:00:00", "2026-11-10T09:00:00"),
    ("2026-11-10T06:00:00-03:00", "2026-11-10T09:00:00"),
    (None, None), ("", ""),
])
def test_para_saida_sem_fuso(valor, esperado):
    assert horarios.para_saida(valor) == esperado


def test_para_banco_e_ida_e_volta():
    gravado = horarios.para_banco(horarios.normalizar_entrada("2026-11-10T09:00"))
    assert gravado == "2026-11-10T09:00:00+00:00"
    assert horarios.para_saida(gravado) == "2026-11-10T09:00:00"


def test_hoje_e_no_fuso_da_clinica():
    assert horarios.hoje() == datetime.now(ZoneInfo("America/Sao_Paulo")).date()

"""Seção 25.3 — a API não sobe sem as chaves obrigatórias."""

import pytest

from config import Config
from app import create_app


@pytest.mark.parametrize("chave", [None, "dev-secret", "troque-por-uma-chave-aleatoria", "curta-demais"])
def test_nao_sobe_sem_chave_jwt_valida(monkeypatch, chave):
    monkeypatch.setattr(Config, "JWT_SECRET", chave)
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        create_app()


def test_nao_sobe_sem_banco(monkeypatch):
    monkeypatch.setattr(Config, "DATABASE_URL", None)
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        create_app()


def test_sobe_com_configuracao_completa():
    assert Config.problemas() == []
    assert create_app() is not None

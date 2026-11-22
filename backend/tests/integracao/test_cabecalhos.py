"""Cabeçalhos de segurança HTTP (app/seguranca.py)."""

import pytest

pytestmark = pytest.mark.rotas


def test_respostas_da_api_levam_os_cabecalhos_de_seguranca(client):
    h = client.get("/api/health").headers
    assert h["X-Content-Type-Options"] == "nosniff"
    assert h["X-Frame-Options"] == "DENY"
    assert h["Referrer-Policy"] == "no-referrer"
    assert "default-src 'none'" in h["Content-Security-Policy"]
    assert "frame-ancestors 'none'" in h["Content-Security-Policy"]
    assert h["Cache-Control"] == "no-store"


def test_erros_tambem_levam_os_cabecalhos(client):
    h = client.get("/api/pacientes/").headers  # 401 sem token
    assert h["X-Content-Type-Options"] == "nosniff"
    assert "Content-Security-Policy" in h


def test_hsts_so_quando_a_requisicao_chega_por_https(client):
    assert "Strict-Transport-Security" not in client.get("/api/health").headers
    https = client.get("/api/health", base_url="https://localhost").headers
    assert https["Strict-Transport-Security"].startswith("max-age=")


def test_proxy_https_ativa_hsts(client):
    """Atrás do proxy do provedor, o HTTPS chega no X-Forwarded-Proto."""
    h = client.get("/api/health", headers={"X-Forwarded-Proto": "https"}).headers
    assert "Strict-Transport-Security" in h


def test_rota_de_arquivos_fica_sem_csp_para_abrir_pdf(client):
    h = client.get("/api/storage/nao-existe").headers
    assert "Content-Security-Policy" not in h
    assert h["X-Content-Type-Options"] == "nosniff"

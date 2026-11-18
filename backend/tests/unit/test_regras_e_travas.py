"""Regras puras (sem banco): detecção de MIME, regras sanitárias, status do
estoque e as travas do seed de demonstração."""

import re

import pytest

import seed_demo
from seed_demo import SeedBloqueado, verificar_ambiente, ler_configuracao
from app.imagens.routes import detectar_mime, SIGNED_URL_TTL
from app.estoque.routes import status_do_item
from app.esterilizacao.routes import resultado_do_ciclo, estado_inicial_do_pacote


def _ler_texto(caminho):
    with open(caminho, encoding="utf-8") as f:
        return f.read()


# ---- uploads ----------------------------------------------------------------

@pytest.mark.parametrize("conteudo,mime", [
    (b"\x89PNG\r\n\x1a\n" + b"\0" * 8, "image/png"), (b"\xff\xd8\xff\xe0", "image/jpeg"),
    (b"GIF89a....", "image/gif"), (b"GIF87a....", "image/gif"),
    (b"RIFF\x24\x00\x00\x00WEBPVP8 ", "image/webp"), (b"%PDF-1.7\n", "application/pdf"),
    (b"<html><script>alert(1)</script>", None), (b"MZ\x90\x00", None),
    (b"RIFF\x00\x00\x00\x00WAVE", None), (b"", None), (b"lixo antes %PDF-1.7", None),
])
def test_detectar_mime(conteudo, mime):
    assert detectar_mime(conteudo) == mime


def test_link_assinado_de_uma_hora():
    assert SIGNED_URL_TTL == 3600


# ---- regras de negócio --------------------------------------------------------

@pytest.mark.parametrize("q,b,esperado", [
    ("Aprovado", "Aprovado", "Aprovado"), ("Aprovado", "Não realizado", "Aprovado"),
    ("Aprovado", "Pendente", "Pendente"), ("Pendente", "Aprovado", "Pendente"),
    ("Reprovado", "Aprovado", "Reprovado"), ("Aprovado", "Reprovado", "Reprovado"),
])
def test_resultado_do_ciclo(q, b, esperado):
    assert resultado_do_ciclo(q, b) == esperado


def test_estado_inicial_do_pacote():
    assert estado_inicial_do_pacote("Aprovado") == "Disponível"
    assert estado_inicial_do_pacote("Reprovado") == "Bloqueado"
    assert estado_inicial_do_pacote("Pendente") == "Aguardando liberação"


@pytest.mark.parametrize("qtd,minimo,status", [(0, 5, "Esgotado"), (5, 5, "Estoque baixo"), (6, 5, "Normal")])
def test_status_do_item(qtd, minimo, status):
    assert status_do_item(qtd, minimo) == status


# ---- seed ---------------------------------------------------------------------

ENV_OK = {
    "APP_ENV": "development",
    "SEED_OWNER_EMAIL": "dono.demo@example.com", "SEED_OWNER_PASSWORD": "senha-dono-demo-1",
    "SEED_RECEPCAO_EMAIL": "recep.demo@example.com", "SEED_RECEPCAO_PASSWORD": "senha-recep-demo-1",
    "SEED_ESPECIALISTA_EMAIL": "espec.demo@example.com", "SEED_ESPECIALISTA_PASSWORD": "senha-espec-demo-1",
}


@pytest.mark.parametrize("env", [
    {"APP_ENV": "production"}, {"APP_ENV": "staging"}, {},
    {"APP_ENV": "development", "RAILWAY_ENVIRONMENT": "production"},
    {"APP_ENV": "development", "RAILWAY_ENVIRONMENT_NAME": "production"},
    {"APP_ENV": "local", "RAILWAY_PROJECT_ID": "abc"},
])
def test_seed_bloqueado_fora_do_ambiente_local(env):
    with pytest.raises(SeedBloqueado):
        verificar_ambiente(env)


@pytest.mark.parametrize("app_env", ["development", "local", "DEVELOPMENT"])
def test_seed_permitido_em_ambiente_local(app_env):
    verificar_ambiente({"APP_ENV": app_env})


@pytest.mark.parametrize("faltando", [k for k in ENV_OK if k.startswith("SEED_")])
def test_seed_credenciais_obrigatorias(faltando):
    with pytest.raises(SeedBloqueado) as e:
        ler_configuracao({k: v for k, v in ENV_OK.items() if k != faltando})
    assert faltando in str(e.value)


def test_seed_senha_curta_e_emails_repetidos():
    with pytest.raises(SeedBloqueado):
        ler_configuracao({**ENV_OK, "SEED_RECEPCAO_PASSWORD": "curta"})
    with pytest.raises(SeedBloqueado):
        ler_configuracao({**ENV_OK, "SEED_RECEPCAO_EMAIL": ENV_OK["SEED_OWNER_EMAIL"]})


def test_seed_sem_senhas_ou_emails_fixos_no_codigo():
    fonte = _ler_texto(seed_demo.__file__)
    assert not re.search(r"@(gmail|hotmail|outlook|yahoo|bytedonto)\.", fonte, re.I)
    assert not re.search(r"(SENHA|PASSWORD)\w*\s*=\s*[\"'][^\"']+[\"']", fonte)
    emails = re.findall(r"[\w.+-]+@[\w-]+\.[\w.]+", fonte)
    assert all(e.endswith("@example.com") for e in emails), emails

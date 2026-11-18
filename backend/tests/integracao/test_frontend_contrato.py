"""Contrato com o frontend: toda chamada /api/... que o React faz existe no
backend unificado com o mesmo método (nenhuma tela recebe 404/405).

As chamadas são extraídas do próprio código do frontend (não de uma lista
mantida à mão), então uma rota nova no frontend sem backend quebra este teste.
"""

import glob
import os
import re

import pytest
from werkzeug.exceptions import MethodNotAllowed, NotFound


def _ler_texto(caminho):
    with open(caminho, encoding="utf-8") as f:
        return f.read()

pytestmark = pytest.mark.rotas

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
FRONTEND_SRC = os.path.join(RAIZ, "frontend", "src")

_TEMPLATE_API = re.compile(r"`\$\{API_URL\}(/api/[^`]*)`")
_REQ_ESTOQUE = re.compile(r"reqEstoque\(token,\s*[`\"]([^`\"]*)[`\"](?:\s*,\s*\{([^}]*)\})?")
_METODO = re.compile(r"method:\s*[\"'](\w+)[\"']")


def _normalizar(caminho):
    caminho = re.sub(r"(?<=/)\$\{[^}]+\}", "x", caminho)   # /${id} -> /x
    caminho = re.sub(r"\$\{[^}]+\}", "", caminho)          # ...${sufixo} -> ...
    return caminho.split("?", 1)[0]


def _fim_da_chamada(texto, achados, i):
    """A chamada de uma URL termina no próximo `export` (outra função do api.js)
    ou na próxima URL passada direto a um fetch( (outra chamada no componente)."""
    inicio = achados[i].end()
    limites = [len(texto)]
    proximo_export = texto.find("export ", inicio)
    if proximo_export != -1:
        limites.append(proximo_export)
    for m in achados[i + 1:]:
        if texto[max(0, m.start() - 6):m.start()] == "fetch(":
            limites.append(m.start())
            break
    return min(limites)


def chamadas_do_frontend():
    chamadas = set()
    for arquivo in glob.glob(os.path.join(FRONTEND_SRC, "**", "*.js*"), recursive=True):
        texto = _ler_texto(arquivo)
        origem = os.path.relpath(arquivo, RAIZ)
        achados = list(_TEMPLATE_API.finditer(texto))
        for i, m in enumerate(achados):
            caminho = m.group(1)
            if caminho.startswith("/api/estoque$"):
                continue  # base do helper reqEstoque (tratado abaixo)
            metodo = _METODO.search(texto[m.end():_fim_da_chamada(texto, achados, i)])
            chamadas.add(((metodo.group(1) if metodo else "GET").upper(), _normalizar(caminho), origem))
        for m in _REQ_ESTOQUE.finditer(texto):
            metodo = _METODO.search(m.group(2) or "")
            chamadas.add(((metodo.group(1) if metodo else "GET").upper(),
                          _normalizar("/api/estoque" + m.group(1)), origem))
    return sorted(chamadas)


CHAMADAS = chamadas_do_frontend()


def test_extraiu_as_chamadas_do_frontend():
    caminhos = {c[1] for c in CHAMADAS}
    # sanidade do extrator: módulos antigos e migrados aparecem
    for esperado in ("/api/auth/login", "/api/pacientes/", "/api/estoque/itens", "/api/estoque/saidas",
                     "/api/estoque/fornecedores/x", "/api/imagens/upload", "/api/dashboard/metricas"):
        assert esperado in caminhos, esperado
    assert len(CHAMADAS) >= 40


@pytest.mark.parametrize("metodo,caminho,origem", CHAMADAS, ids=[f"{m} {c}" for m, c, _ in CHAMADAS])
def test_rota_do_frontend_existe_no_backend(app, metodo, caminho, origem):
    adaptador = app.url_map.bind("localhost")
    try:
        adaptador.match(caminho, method=metodo)
    except NotFound:
        pytest.fail(f"{origem}: {metodo} {caminho} não existe no backend (404)")
    except MethodNotAllowed:
        pytest.fail(f"{origem}: {metodo} {caminho} existe, mas não aceita {metodo} (405)")

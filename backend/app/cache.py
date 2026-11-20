"""Cache curto (TTL) das leituras mais frequentes da API.

O que fica em cache (só respostas 200, já prontas em JSON):
  * lista de pacientes (página + busca) e a lista curta /pacientes/opcoes
  * agenda (GET /consultas com período) para quem NÃO vê prontuário
  * dados da clínica e lista de clínicas
  * equipe / profissionais (GET /usuarios)
  * resumo do financeiro (cards e gráficos)

O que NUNCA fica em cache: prontuário (ficha do paciente, evolução clínica,
odontograma, anamnese, planos), documentos/termos/imagens e URLs assinadas.

Segurança (dados de saúde — LGPD):
  * A chave SEMPRE inclui clinica_id E usuario_id (além do recurso e da query
    string). Uma clínica nunca recebe a resposta de outra, e cada usuário só
    reaproveita as próprias respostas (as permissões podem mudar o conteúdo).
  * O cache fica DEPOIS da autenticação e do RBAC: get_contexto() e as checagens
    de permissão rodam em toda requisição; só a leitura do banco é poupada.
  * Toda escrita (POST/PUT/PATCH/DELETE) invalida os recursos afetados — veja
    INVALIDA_POR_MODULO e registrar_invalidacao(). Em dúvida, limpa tudo.

Limites: o cache vive na memória do processo. Em produção roda um único worker
(gunicorn run:app). Com vários workers/instâncias cada um teria o seu cache e uma
escrita só invalidaria o do próprio processo — nesse caso use CACHE_TTL_SECONDS=0
(desliga) ou troque este módulo por Redis.
"""

import json
import threading
import time
from collections import OrderedDict

from flask import Response, request

from config import Config

MAX_ENTRADAS = 2000

_lock = threading.Lock()
_dados = OrderedDict()  # chave -> (expira_em, corpo_json)
_estatisticas = {"hits": 0, "misses": 0}

# Escrita num módulo (blueprint) -> recursos em cache que ficam desatualizados.
# "*" = limpa tudo (mudanças de equipe, permissões ou clínica ativa afetam várias telas).
INVALIDA_POR_MODULO = {
    "pacientes": {"pacientes", "consultas"},       # agenda mostra o nome do paciente
    "consultas": {"consultas", "pacientes"},       # lista de pacientes mostra a última consulta
    "financeiro": {"financeiro"},
    "planos": {"financeiro"},                      # concluir item do plano gera lançamento
    "imagens": set(),                              # nada de imagens/documentos em cache
    "estoque": set(),
    "esterilizacao": set(),
    "usuarios": {"*"},
    "clinicas": {"*"},
    "auth": {"*"},
}


def ttl():
    return max(0, int(getattr(Config, "CACHE_TTL_SECONDS", 0) or 0))


def _chave(recurso, ctx):
    params = json.dumps(sorted(request.args.items(multi=True)), ensure_ascii=False)
    return (recurso, str(ctx.get("clinica_id")), str(ctx.get("user_id")), request.path, params)


def responder(recurso, ctx, gerar):
    """Devolve a resposta JSON do cache ou chama gerar() -> (payload, status).

    Só guarda status 200 e só quando há clínica e usuário identificados."""
    duracao = ttl()
    if duracao <= 0 or not ctx.get("clinica_id") or not ctx.get("user_id"):
        payload, status = gerar()
        return _resposta(json.dumps(payload, ensure_ascii=False), status, "BYPASS")

    chave = _chave(recurso, ctx)
    agora = time.monotonic()
    with _lock:
        entrada = _dados.get(chave)
        if entrada and entrada[0] > agora:
            _dados.move_to_end(chave)
            _estatisticas["hits"] += 1
            return _resposta(entrada[1], 200, "HIT")
        _dados.pop(chave, None)

    payload, status = gerar()
    corpo = json.dumps(payload, ensure_ascii=False)
    if status == 200:
        with _lock:
            _estatisticas["misses"] += 1
            _dados[chave] = (agora + duracao, corpo)
            while len(_dados) > MAX_ENTRADAS:
                _dados.popitem(last=False)
    return _resposta(corpo, status, "MISS")


def _resposta(corpo, status, origem):
    resp = Response(corpo, status=status, mimetype="application/json")
    # Ajuda a demonstrar/depurar; não expõe dado nenhum.
    resp.headers["X-Cache"] = origem
    return resp


def invalidar(*recursos):
    """Remove do cache os recursos indicados (de TODAS as clínicas). "*" limpa tudo."""
    alvo = set(recursos)
    with _lock:
        if "*" in alvo:
            _dados.clear()
            return
        for chave in [k for k in _dados if k[0] in alvo]:
            del _dados[chave]


def limpar_tudo():
    invalidar("*")


def estatisticas():
    with _lock:
        return {**_estatisticas, "entradas": len(_dados)}


def registrar_invalidacao(app):
    """after_request: qualquer escrita invalida o que ela pode ter alterado.

    Roda mesmo quando a escrita falha (status 4xx/5xx), porque uma falha no meio
    pode ter gravado parte dos dados. Módulo desconhecido -> limpa tudo."""

    @app.after_request
    def _invalidar_apos_escrita(resposta):
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            recursos = INVALIDA_POR_MODULO.get(request.blueprint or "", {"*"})
            if recursos:
                invalidar(*recursos)
        return resposta

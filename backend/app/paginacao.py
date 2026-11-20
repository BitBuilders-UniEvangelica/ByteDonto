"""Paginação das listagens: ?page=1&per_page=20.

Contrato (igual em todas as rotas que paginam):
  * page      — inteiro >= 1 (padrão 1). Menor que 1 vira 1.
  * per_page  — inteiro entre 20 e 50 (padrão 20). Fora do intervalo é ajustado
                para o limite mais próximo (pedir 5 devolve 20, pedir 500 devolve 50).
  * valor não numérico em page/per_page -> HTTP 400.
  * página além do fim -> items vazio, com o total correto.

Resposta: {"items": [...], "page": 1, "per_page": 20, "total": 137}

O banco devolve só a fatia pedida (LIMIT/OFFSET via .range()) e o total vem do
count="exact" da mesma consulta — nada de carregar a tabela inteira.
"""

from dataclasses import dataclass

PER_PAGE_PADRAO = 20
PER_PAGE_MIN = 20
PER_PAGE_MAX = 50


@dataclass(frozen=True)
class Paginacao:
    page: int
    per_page: int

    @property
    def inicio(self):
        return (self.page - 1) * self.per_page

    @property
    def fim(self):
        """Índice final INCLUSIVO, como o .range() do postgrest."""
        return self.inicio + self.per_page - 1


def ler_paginacao(args):
    """Lê page/per_page da query string. Levanta ValueError (-> 400) se não forem inteiros."""
    try:
        page = int(args.get("page", 1))
        per_page = int(args.get("per_page", PER_PAGE_PADRAO))
    except (TypeError, ValueError):
        raise ValueError("Os parâmetros 'page' e 'per_page' devem ser números inteiros.")
    return Paginacao(
        page=max(1, page),
        per_page=min(PER_PAGE_MAX, max(PER_PAGE_MIN, per_page)),
    )


def quer_paginacao(args):
    """Rotas em que a paginação é opcional (agenda, financeiro, estoque) só paginam
    quando o cliente manda page ou per_page; sem eles, mantêm o formato antigo (lista)."""
    return "page" in args or "per_page" in args


def _fora_do_intervalo(erro):
    # PostgREST responde 416 / PGRST103 quando o offset passa do total de linhas.
    codigo = str(getattr(erro, "code", "") or "")
    texto = str(getattr(erro, "message", "") or erro)
    return codigo in ("PGRST103", "416") or "PGRST103" in texto or "Range Not Satisfiable" in texto


def buscar_pagina(montar_query, pag):
    """Executa uma página. `montar_query()` devolve um builder NOVO, já com
    select(..., count="exact"), filtros e ordenação — sem range/limit.

    Devolve (itens, total)."""
    try:
        resposta = montar_query().range(pag.inicio, pag.fim).execute()
        itens, total = resposta.data or [], resposta.count
    except Exception as e:
        if not _fora_do_intervalo(e):
            raise
        itens, total = [], None
    if total is None:
        total = montar_query().range(0, 0).execute().count or 0
    return itens, total


def envelope(itens, pag, total):
    return {"items": itens, "page": pag.page, "per_page": pag.per_page, "total": total}

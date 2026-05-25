"""Trilha de auditoria do prontuário eletrônico.

Atende a Resolução CFO 226/2020 (rastreabilidade de alterações no prontuário).
Registra quem alterou, quando, e o diff campo a campo.

Uso:
    registrar_alteracao(
        clinica_id=clinica_id,
        usuario_id=user_id,
        paciente_id=paciente_id,
        tabela="pacientes",
        registro_id=paciente_id,
        acao="UPDATE",
        antes={"nome": "Maria"},
        depois={"nome": "Maria Silva"},
    )

Falhas de auditoria nunca derrubam a operação principal — são logadas e seguem.
"""

import logging
from app.database import supabase

log = logging.getLogger(__name__)

# Campos sensíveis cujo valor não é logado integralmente (apenas o fato de mudaram).
CAMPOS_OMITIDOS = {"senha", "password", "token"}


def _diff(antes, depois):
    """Calcula o diff entre dois dicts. Retorna { campo: { antes, depois } }."""
    antes = antes or {}
    depois = depois or {}
    mudancas = {}
    for chave in set(antes.keys()) | set(depois.keys()):
        v_antes = antes.get(chave)
        v_depois = depois.get(chave)
        if v_antes == v_depois:
            continue
        if chave in CAMPOS_OMITIDOS:
            mudancas[chave] = {"antes": "***", "depois": "***"}
        else:
            mudancas[chave] = {"antes": v_antes, "depois": v_depois}
    return mudancas


def registrar_alteracao(
    *,
    clinica_id,
    usuario_id,
    tabela,
    registro_id,
    acao,
    paciente_id=None,
    antes=None,
    depois=None,
):
    """Grava uma linha em auditoria_prontuario. Nunca lança."""
    try:
        if acao == "UPDATE":
            campos = _diff(antes, depois)
            if not campos:
                return  # nada mudou de fato; não polui a auditoria
        elif acao == "INSERT":
            campos = {k: {"antes": None, "depois": v} for k, v in (depois or {}).items() if k not in CAMPOS_OMITIDOS}
        elif acao == "DELETE":
            campos = {k: {"antes": v, "depois": None} for k, v in (antes or {}).items() if k not in CAMPOS_OMITIDOS}
        else:
            campos = {}

        supabase.table("auditoria_prontuario").insert({
            "clinica_id": clinica_id,
            "paciente_id": paciente_id,
            "usuario_id": usuario_id,
            "tabela": tabela,
            "registro_id": registro_id,
            "acao": acao,
            "campos": campos,
        }).execute()
    except Exception as e:
        log.warning("Falha ao registrar auditoria de %s/%s: %s", tabela, registro_id, e)

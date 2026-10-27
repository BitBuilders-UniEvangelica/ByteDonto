"""Autenticação e autorização centralizadas (RBAC).

Substitui as cópias de get_token/get_user_clinica espalhadas por cada módulo,
unificando a resolução do usuário, o controle de permissões por papel e o
tratamento de erro das rotas. A clínica considerada é sempre a ATIVA
(usuarios.clinica_id) do usuário autenticado.
"""

from flask import request, jsonify, current_app
from app.database import supabase

# Permissões padrão por papel — fonte única de verdade para o fallback do RBAC.
# Usada quando o perfil não tem uma permissão individual definida em 'permissoes'.
PERMISSOES_PADRAO = {
    "Especialista": {
        "ver_pacientes": True, "editar_pacientes": False,
        "ver_prontuario": True, "editar_prontuario": True,
        "ver_agenda": True, "agendar_consultas": False,
        "cancelar_consultas": False, "ver_financeiro": False,
        "esterilizacao": True,
    },
    "Recepção": {
        "ver_pacientes": True, "editar_pacientes": True,
        "ver_prontuario": False, "editar_prontuario": False,
        "ver_agenda": True, "agendar_consultas": True,
        "cancelar_consultas": True, "ver_financeiro": True,
        "esterilizacao": False,
    },
}


class AuthError(Exception):
    """Erro de autenticação/autorização com status HTTP associado."""

    def __init__(self, mensagem, status):
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.status = status


def get_token(req=None):
    req = req or request
    return req.headers.get("Authorization", "").replace("Bearer ", "")


def get_contexto(token):
    """Resolve o contexto do usuário autenticado.

    Retorna dict {user_id, clinica_id, papel, permissoes}.
    - Token ausente/inválido -> AuthError(401).
    - Perfil ainda não criado na tabela usuarios -> clinica_id/papel ficam None
      (cabe à rota decidir: lista vazia ou 403). Não recriamos perfil silenciosamente.
    """
    if not token:
        raise AuthError("Não autorizado.", 401)
    try:
        user = supabase.auth.get_user(token).user
    except Exception:
        raise AuthError("Sessão expirada ou token inválido.", 401)
    if not user:
        raise AuthError("Sessão expirada ou token inválido.", 401)

    res = (
        supabase.table("usuarios")
        .select("clinica_id, papel, permissoes")
        .eq("id", user.id)
        .maybe_single()
        .execute()
    )
    perfil = res.data if res else None
    if not perfil:
        return {"user_id": user.id, "clinica_id": None, "papel": None, "permissoes": {}}
    return {
        "user_id": user.id,
        "clinica_id": perfil.get("clinica_id"),
        "papel": perfil.get("papel"),
        "permissoes": perfil.get("permissoes") or {},
    }


def get_user_clinica(token):
    """Compat: (user_id, clinica_id). Delega ao contexto unificado."""
    ctx = get_contexto(token)
    return ctx["user_id"], ctx["clinica_id"]


def tem_permissao(ctx, chave):
    """True se o usuário tem a permissão. O Dono sempre pode tudo."""
    if ctx.get("papel") == "Dono":
        return True
    permissoes = ctx.get("permissoes") or {}
    if chave in permissoes:
        return bool(permissoes[chave])
    padrao = PERMISSOES_PADRAO.get(ctx.get("papel"), {})
    return bool(padrao.get(chave, False))


def exigir_permissao(ctx, chave):
    """Levanta AuthError(403) se faltar a permissão."""
    if not tem_permissao(ctx, chave):
        raise AuthError("Você não tem permissão para esta ação.", 403)


def exigir_papel(ctx, *papeis):
    """Levanta AuthError(403) se o papel do usuário não estiver na lista."""
    if ctx.get("papel") not in papeis:
        raise AuthError("Você não tem permissão para esta ação.", 403)


def exigir_clinica(ctx):
    """Levanta AuthError(403) se o usuário não tiver clínica ativa. Retorna o clinica_id."""
    if not ctx.get("clinica_id"):
        raise AuthError("Perfil sem clínica vinculada. Contate o proprietário.", 403)
    return ctx["clinica_id"]


def eh_dono_da_clinica(user_id, clinica_id):
    """True se o usuário é o dono (clinicas.dono_id) da clínica informada."""
    if not clinica_id:
        return False
    res = (
        supabase.table("clinicas")
        .select("dono_id")
        .eq("id", clinica_id)
        .maybe_single()
        .execute()
    )
    return bool(res and res.data and res.data.get("dono_id") == user_id)


def pertence_a_clinica(tabela, registro_id, clinica_id, coluna="id"):
    """True se existe um registro na 'tabela' com id e clinica_id informados.

    Usado para barrar IDOR: impede vincular paciente/atendimento/item de outra
    clínica num lançamento/plano. Se registro_id for None, considera 'sem vínculo'
    (True) — quem exige obrigatoriedade é a validação do campo, não esta checagem.
    """
    if registro_id is None:
        return True
    res = (
        supabase.table(tabela)
        .select(coluna)
        .eq(coluna, registro_id)
        .eq("clinica_id", clinica_id)
        .maybe_single()
        .execute()
    )
    return bool(res and res.data)


def tratar_erro(e):
    """Converte exceções em respostas HTTP sem vazar detalhes internos.

    AuthError -> seu status (401/403). Qualquer outra -> 500 genérico, com o
    stack trace registrado no log do servidor (não exposto ao cliente).
    """
    if isinstance(e, AuthError):
        return jsonify({"error": e.mensagem}), e.status
    current_app.logger.exception("Erro não tratado em rota")
    return jsonify({"error": "Erro interno do servidor."}), 500

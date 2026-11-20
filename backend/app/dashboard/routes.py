from flask import Blueprint, request, jsonify
from app.database import supabase
from app.auth_utils import get_token, get_contexto, eh_dono_da_clinica, tem_permissao, tratar_erro
from app.horarios import hoje as hoje_na_clinica, inicio_do_dia, fim_do_dia

dashboard_bp = Blueprint("dashboard", __name__)

METRICAS_ZERADAS = {
    "total_pacientes": 0,
    "consultas_hoje": 0,
    "total_consultas": 0,
    "consultas_finalizadas": 0,
    "total_especialistas": 0,
    "total_membros": 0,
    "receita_mes": 0,
    "pendente_mes": 0,
}

# Métricas financeiras só vão para quem tem a permissão 'ver_financeiro'.
METRICAS_FINANCEIRAS = ("receita_mes", "pendente_mes")


def _filtrar_metricas(ctx, metricas):
    if not tem_permissao(ctx, "ver_financeiro"):
        return {k: v for k, v in metricas.items() if k not in METRICAS_FINANCEIRAS}
    return metricas


@dashboard_bp.route("/metricas", methods=["GET"])
def metricas():
    token = get_token(request)
    if not token:
        return jsonify({"error": "Não autorizado"}), 401

    try:
        ctx = get_contexto(token)
        clinica_id = ctx["clinica_id"]

        # O Dono pode pedir métricas de OUTRA clínica que ele possui (?clinica_id=).
        # Só é permitido se ele for o dono — senão ignora e usa a clínica ativa.
        clinica_solicitada = request.args.get("clinica_id")
        if clinica_solicitada and clinica_solicitada != clinica_id:
            if eh_dono_da_clinica(ctx["user_id"], clinica_solicitada):
                clinica_id = clinica_solicitada
            else:
                return jsonify({"error": "Você não tem acesso a esta clínica"}), 403

        # Usuário ainda sem clínica vinculada — devolve métricas zeradas
        if not clinica_id:
            return jsonify(_filtrar_metricas(ctx, dict(METRICAS_ZERADAS))), 200

        # "Hoje" no fuso da clínica (o servidor roda em UTC) e na mesma convenção
        # de horário de parede da agenda (app/horarios.py).
        dia = hoje_na_clinica()
        primeiro_dia_mes = dia.replace(day=1).isoformat()

        # Total de pacientes ativos
        pacientes = (
            supabase.table("pacientes")
            .select("id")
            .eq("clinica_id", clinica_id)
            .execute()
        )
        total_pacientes = len(pacientes.data)

        # Consultas de hoje
        consultas_hoje_res = (
            supabase.table("atendimentos")
            .select("id, status")
            .eq("clinica_id", clinica_id)
            .gte("data_agendada", inicio_do_dia(dia))
            .lte("data_agendada", fim_do_dia(dia))
            .execute()
        )
        consultas_hoje = len(consultas_hoje_res.data)

        # Total de consultas (todas) e quantas estão finalizadas
        consultas_todas = (
            supabase.table("atendimentos")
            .select("status")
            .eq("clinica_id", clinica_id)
            .execute()
        )
        total_consultas = len(consultas_todas.data or [])
        consultas_finalizadas = sum(
            1 for c in (consultas_todas.data or []) if c.get("status") == "Finalizado"
        )

        # Equipe: especialistas e total de membros da clínica
        membros = (
            supabase.table("usuarios")
            .select("id, papel")
            .eq("clinica_id", clinica_id)
            .execute()
        )
        total_membros = len(membros.data or [])
        total_especialistas = sum(
            1 for m in (membros.data or []) if m.get("papel") == "Especialista"
        )

        # Receita e pendências do mês (só consultadas por quem pode ver o financeiro)
        receita_mes = pendente_mes = 0
        if tem_permissao(ctx, "ver_financeiro"):
            fat_mes = (
                supabase.table("faturamento")
                .select("valor, status_pagamento")
                .eq("clinica_id", clinica_id)
                .gte("created_at", f"{primeiro_dia_mes}T00:00:00")
                .execute()
            )
            receita_mes = sum(
                float(f.get("valor") or 0) for f in fat_mes.data if f.get("status_pagamento") == "Pago"
            )
            pendente_mes = sum(
                float(f.get("valor") or 0) for f in fat_mes.data if f.get("status_pagamento") == "Pendente"
            )

        return jsonify(_filtrar_metricas(ctx, {
            "total_pacientes": total_pacientes,
            "consultas_hoje": consultas_hoje,
            "total_consultas": total_consultas,
            "consultas_finalizadas": consultas_finalizadas,
            "total_especialistas": total_especialistas,
            "total_membros": total_membros,
            "receita_mes": receita_mes,
            "pendente_mes": pendente_mes,
        })), 200
    except Exception as e:
        return tratar_erro(e)

from flask import Blueprint, request, jsonify
from app.database import supabase
from datetime import date

dashboard_bp = Blueprint("dashboard", __name__)


def get_token(req):
    return req.headers.get("Authorization", "").replace("Bearer ", "")


def get_user_clinica(token):
    user = supabase.auth.get_user(token).user
    perfil = supabase.table("usuarios").select("clinica_id").eq("id", user.id).single().execute()
    return user.id, perfil.data["clinica_id"]


@dashboard_bp.route("/metricas", methods=["GET"])
def metricas():
    token = get_token(request)
    if not token:
        return jsonify({"error": "Não autorizado"}), 401

    try:
        _, clinica_id = get_user_clinica(token)

        # Usuário ainda sem clínica vinculada — devolve métricas zeradas
        if not clinica_id:
            return jsonify({
                "total_pacientes": 0,
                "consultas_hoje": 0,
                "total_especialistas": 0,
                "receita_mes": 0,
                "pendente_mes": 0,
            }), 200

        hoje = date.today().isoformat()
        primeiro_dia_mes = date.today().replace(day=1).isoformat()

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
            .gte("data_agendada", f"{hoje}T00:00:00")
            .lte("data_agendada", f"{hoje}T23:59:59")
            .execute()
        )
        consultas_hoje = len(consultas_hoje_res.data)

        # Total de especialistas
        especialistas = (
            supabase.table("usuarios")
            .select("id")
            .eq("clinica_id", clinica_id)
            .eq("papel", "Especialista")
            .execute()
        )
        total_especialistas = len(especialistas.data)

        # Receita e pendências do mês
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

        return jsonify({
            "total_pacientes": total_pacientes,
            "consultas_hoje": consultas_hoje,
            "total_especialistas": total_especialistas,
            "receita_mes": receita_mes,
            "pendente_mes": pendente_mes,
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

from collections import defaultdict
from datetime import datetime
from flask import Blueprint, request, jsonify
from app.database import supabase
from app.validators import campo_obrigatorio, validar_valor, validar_enum

financeiro_bp = Blueprint("financeiro", __name__)

STATUS_PAGAMENTO_VALIDOS = {"Pago", "Pendente", "Cancelado"}
FORMAS_PAGAMENTO_VALIDAS = {
    "Dinheiro", "Cartão Débito", "Cartão Crédito", "Pix", "Convênio",
}


def get_token(req):
    return req.headers.get("Authorization", "").replace("Bearer ", "")


def get_user_clinica(token):
    user = supabase.auth.get_user(token).user
    perfil = supabase.table("usuarios").select("clinica_id").eq("id", user.id).single().execute()
    return user.id, perfil.data["clinica_id"]


@financeiro_bp.route("/", methods=["GET"])
def listar_lancamentos():
    token = get_token(request)
    if not token:
        return jsonify({"error": "Não autorizado"}), 401

    try:
        _, clinica_id = get_user_clinica(token)

        query = (
            supabase.table("faturamento")
            .select("*, pacientes(nome), dentista:usuarios!dentista_responsavel(nome)")
            .eq("clinica_id", clinica_id)
            .order("created_at", desc=True)
        )

        status = request.args.get("status")
        if status:
            query = query.eq("status_pagamento", status)

        result = query.execute()
        return jsonify(result.data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@financeiro_bp.route("/", methods=["POST"])
def criar_lancamento():
    token = get_token(request)
    if not token:
        return jsonify({"error": "Não autorizado"}), 401

    try:
        _, clinica_id = get_user_clinica(token)
        data = request.get_json() or {}

        try:
            campo_obrigatorio(data.get("paciente_id"), "paciente_id")
            valor = validar_valor(data.get("valor"))
            status_pagamento = data.get("status_pagamento")
            if status_pagamento is not None:
                validar_enum(status_pagamento, STATUS_PAGAMENTO_VALIDOS, "status_pagamento")
            forma_pagamento = data.get("forma_pagamento")
            if forma_pagamento is not None:
                validar_enum(forma_pagamento, FORMAS_PAGAMENTO_VALIDAS, "forma_pagamento")
        except ValueError as e:
            return jsonify({"error": str(e)}), 400

        novo_lancamento = {
            "clinica_id": clinica_id,
            "paciente_id": data.get("paciente_id"),
            "atendimento_id": data.get("atendimento_id"),
            "plano_item_id": data.get("plano_item_id"),
            "dentista_responsavel": data.get("dentista_responsavel"),
            "valor": valor,
            "descricao": (data.get("descricao") or "").strip() or None,
            "forma_pagamento": data.get("forma_pagamento"),
            "status_pagamento": data.get("status_pagamento"),
        }

        # Remove keys com valor None para usar defaults do banco
        novo_lancamento = {k: v for k, v in novo_lancamento.items() if v is not None}

        result = supabase.table("faturamento").insert(novo_lancamento).execute()
        return jsonify(result.data[0]), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@financeiro_bp.route("/<id>", methods=["PUT"])
def atualizar_lancamento(id):
    token = get_token(request)
    if not token:
        return jsonify({"error": "Não autorizado"}), 401

    try:
        _, clinica_id = get_user_clinica(token)
        data = request.get_json()

        CAMPOS_PERMITIDOS = {"status_pagamento", "forma_pagamento", "valor", "descricao"}
        payload = {k: v for k, v in data.items() if k in CAMPOS_PERMITIDOS}

        if not payload:
            return jsonify({"error": "Nenhum campo válido para atualizar"}), 400

        try:
            if "valor" in payload:
                payload["valor"] = validar_valor(payload.get("valor"))
            if "status_pagamento" in payload:
                validar_enum(payload.get("status_pagamento"), STATUS_PAGAMENTO_VALIDOS, "status_pagamento")
            if "forma_pagamento" in payload:
                validar_enum(payload.get("forma_pagamento"), FORMAS_PAGAMENTO_VALIDAS, "forma_pagamento")
        except ValueError as e:
            return jsonify({"error": str(e)}), 400

        # Verifica que o lançamento pertence à clínica antes de atualizar
        check = (
            supabase.table("faturamento")
            .select("id")
            .eq("id", id)
            .eq("clinica_id", clinica_id)
            .single()
            .execute()
        )

        if not check.data:
            return jsonify({"error": "Lançamento não encontrado"}), 404

        result = (
            supabase.table("faturamento")
            .update(payload)
            .eq("id", id)
            .eq("clinica_id", clinica_id)
            .execute()
        )
        return jsonify(result.data[0]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@financeiro_bp.route("/repasses", methods=["GET"])
def repasses_dentista():
    """Relatório de repasse mensal: quanto cada dentista produziu e quanto recebe.

    Query string: ?mes=YYYY-MM (padrão = mês corrente).
    Considera apenas lançamentos PAGO no mês.
    Aplica o percentual_repasse cadastrado no perfil do dentista.
    """
    token = get_token(request)
    if not token:
        return jsonify({"error": "Não autorizado"}), 401

    try:
        _, clinica_id = get_user_clinica(token)
        mes = request.args.get("mes") or datetime.utcnow().strftime("%Y-%m")
        try:
            datetime.strptime(mes, "%Y-%m")
        except ValueError:
            return jsonify({"error": "Parâmetro 'mes' inválido. Use YYYY-MM."}), 400

        # Faturamento pago no mês
        lancamentos = (
            supabase.table("faturamento")
            .select("valor, dentista_responsavel")
            .eq("clinica_id", clinica_id)
            .eq("status_pagamento", "Pago")
            .gte("created_at", f"{mes}-01T00:00:00")
            .lt("created_at", _proximo_mes(mes))
            .execute()
        )

        dentistas = (
            supabase.table("usuarios")
            .select("id, nome, papel, percentual_repasse")
            .eq("clinica_id", clinica_id)
            .in_("papel", ["Especialista", "Dono"])
            .execute()
        )
        info = {d["id"]: d for d in dentistas.data or []}

        producao = defaultdict(float)
        for l in lancamentos.data or []:
            did = l.get("dentista_responsavel")
            if did:
                producao[did] += float(l.get("valor") or 0)

        relatorio = []
        for did, total in producao.items():
            dent = info.get(did) or {"nome": "Dentista removido", "percentual_repasse": 0}
            percentual = float(dent.get("percentual_repasse") or 0)
            relatorio.append({
                "dentista_id": did,
                "dentista_nome": dent.get("nome"),
                "percentual_repasse": percentual,
                "producao": round(total, 2),
                "repasse": round(total * percentual / 100, 2),
            })

        # Dentistas sem produção também aparecem (zero) para evitar surpresa
        for did, dent in info.items():
            if did not in producao:
                relatorio.append({
                    "dentista_id": did,
                    "dentista_nome": dent.get("nome"),
                    "percentual_repasse": float(dent.get("percentual_repasse") or 0),
                    "producao": 0.0,
                    "repasse": 0.0,
                })

        relatorio.sort(key=lambda r: r["producao"], reverse=True)

        return jsonify({"mes": mes, "itens": relatorio}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def _proximo_mes(mes):
    """'2026-05' -> '2026-06-01T00:00:00'. Útil pro filtro lt no Supabase."""
    ano, m = mes.split("-")
    ano, m = int(ano), int(m)
    if m == 12:
        ano += 1
        m = 1
    else:
        m += 1
    return f"{ano:04d}-{m:02d}-01T00:00:00"

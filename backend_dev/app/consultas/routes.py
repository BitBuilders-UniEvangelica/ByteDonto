from datetime import datetime, timezone
from flask import Blueprint, request, jsonify
from app.database import supabase
from app.auditoria import registrar_alteracao
from app.validators import campo_obrigatorio, validar_enum
from app.auth_utils import (
    get_token, get_contexto, exigir_permissao, exigir_clinica,
    pertence_a_clinica, tratar_erro,
)

consultas_bp = Blueprint("consultas", __name__)

STATUS_VALIDOS = {"Agendado", "Aguardando", "Cancelado", "Finalizado", "Faltou"}

SELECT_COMPLETO = "*, pacientes(nome), dentista:usuarios!dentista_id(nome)"


def _validar_duracao(d):
    if d is None:
        return None
    try:
        n = int(d)
    except (TypeError, ValueError):
        raise ValueError("Duração deve ser um número inteiro de minutos.")
    if n < 5 or n > 480:
        raise ValueError("Duração deve estar entre 5 e 480 minutos.")
    return n


def _coluna_inexistente(e, coluna):
    """True se o erro do Supabase é por uma coluna ainda não migrada."""
    msg = str(e)
    return "Could not find" in msg and coluna in msg


def _inserir_atendimento(payload):
    """Insere o atendimento; se 'queixa_principal' ainda não existir (migração
    não aplicada), reinsere sem ela em vez de quebrar o agendamento."""
    try:
        return supabase.table("atendimentos").insert(payload).execute()
    except Exception as e:
        if "queixa_principal" in payload and _coluna_inexistente(e, "queixa_principal"):
            payload.pop("queixa_principal", None)
            return supabase.table("atendimentos").insert(payload).execute()
        raise


def _atualizar_atendimento(payload, consulta_id, clinica_id):
    """Atualiza com a mesma degradação graciosa para 'queixa_principal'."""
    def _exec(p):
        return (
            supabase.table("atendimentos")
            .update(p)
            .eq("id", consulta_id)
            .eq("clinica_id", clinica_id)
            .execute()
        )
    try:
        return _exec(payload)
    except Exception as e:
        if "queixa_principal" in payload and _coluna_inexistente(e, "queixa_principal"):
            payload.pop("queixa_principal", None)
            return _exec(payload)
        raise


@consultas_bp.route("/", methods=["GET"])
def listar_consultas():
    token = get_token(request)
    if not token:
        return jsonify({"error": "Não autorizado"}), 401

    try:
        ctx = get_contexto(token)
        clinica_id = ctx["clinica_id"]
        if not clinica_id:
            return jsonify([]), 200

        query = (
            supabase.table("atendimentos")
            .select(SELECT_COMPLETO)
            .eq("clinica_id", clinica_id)
            .order("data_agendada")
        )

        paciente_id = request.args.get("paciente_id")
        if paciente_id:
            query = query.eq("paciente_id", paciente_id)

        result = query.execute()
        return jsonify(result.data), 200
    except Exception as e:
        return tratar_erro(e)


@consultas_bp.route("/", methods=["POST"])
def agendar_consulta():
    token = get_token(request)
    if not token:
        return jsonify({"error": "Não autorizado"}), 401

    try:
        ctx = get_contexto(token)
        exigir_permissao(ctx, "agendar_consultas")
        clinica_id = exigir_clinica(ctx)
        user_id = ctx["user_id"]
        data = request.get_json(silent=True) or {}

        try:
            campo_obrigatorio(data.get("paciente_id"), "paciente_id")
            campo_obrigatorio(data.get("data_agendada"), "data_agendada")
            status = data.get("status") or "Agendado"
            validar_enum(status, STATUS_VALIDOS, "status")
            duracao = _validar_duracao(data.get("duracao_minutos"))
        except ValueError as e:
            return jsonify({"error": str(e)}), 400

        # IDOR: paciente e dentista têm que ser da mesma clínica.
        if not pertence_a_clinica("pacientes", data.get("paciente_id"), clinica_id):
            return jsonify({"error": "Paciente não encontrado nesta clínica"}), 404
        if data.get("dentista_id") and not pertence_a_clinica("usuarios", data.get("dentista_id"), clinica_id):
            return jsonify({"error": "Dentista não encontrado nesta clínica"}), 404

        novo_atendimento = {
            "clinica_id": clinica_id,
            "paciente_id": data.get("paciente_id"),
            "dentista_id": data.get("dentista_id"),
            "data_agendada": data.get("data_agendada"),
            "duracao_minutos": duracao,
            "cadeira": (data.get("cadeira") or "").strip() or None,
            "queixa_principal": data.get("queixa_principal"),
            "procedimentos_descritos": data.get("procedimentos_descritos"),
            "tipo_atendimento": data.get("tipo_atendimento"),
            "status": status,
            "updated_by": user_id,
        }

        # Remove keys with None value to let the DB use its defaults
        novo_atendimento = {k: v for k, v in novo_atendimento.items() if v is not None}

        result = _inserir_atendimento(novo_atendimento)
        novo_id = result.data[0]["id"]

        # Recarrega com join — assim o frontend já recebe o nome do dentista e do paciente
        completo = (
            supabase.table("atendimentos")
            .select(SELECT_COMPLETO)
            .eq("id", novo_id)
            .single()
            .execute()
        )

        registrar_alteracao(
            clinica_id=clinica_id,
            usuario_id=user_id,
            paciente_id=novo_atendimento.get("paciente_id"),
            tabela="atendimentos",
            registro_id=novo_id,
            acao="INSERT",
            depois=result.data[0],
        )

        return jsonify(completo.data), 201
    except Exception as e:
        return tratar_erro(e)


@consultas_bp.route("/<consulta_id>", methods=["PUT"])
def atualizar_consulta(consulta_id):
    token = get_token(request)
    if not token:
        return jsonify({"error": "Não autorizado"}), 401

    try:
        ctx = get_contexto(token)
        clinica_id = exigir_clinica(ctx)
        user_id = ctx["user_id"]
        data = request.get_json(silent=True) or {}

        CAMPOS_PERMITIDOS = {
            "evolucao_clinica", "status", "procedimentos_descritos", "queixa_principal",
            "tipo_atendimento", "data_agendada", "duracao_minutos", "cadeira",
        }
        payload = {k: v for k, v in data.items() if k in CAMPOS_PERMITIDOS}

        if not payload:
            return jsonify({"error": "Nenhum campo válido para atualizar"}), 400

        try:
            if "status" in payload:
                validar_enum(payload["status"], STATUS_VALIDOS, "status")
            if "duracao_minutos" in payload:
                payload["duracao_minutos"] = _validar_duracao(payload["duracao_minutos"])
        except ValueError as e:
            return jsonify({"error": str(e)}), 400

        # Snapshot antes da alteração — auditoria
        atual = (
            supabase.table("atendimentos")
            .select("*")
            .eq("id", consulta_id)
            .eq("clinica_id", clinica_id)
            .maybe_single()
            .execute()
        )
        if not (atual and atual.data):
            return jsonify({"error": "Atendimento não encontrado"}), 404

        payload["updated_by"] = user_id
        payload["updated_at"] = datetime.now(timezone.utc).isoformat()

        result = _atualizar_atendimento(payload, consulta_id, clinica_id)

        registrar_alteracao(
            clinica_id=clinica_id,
            usuario_id=user_id,
            paciente_id=atual.data.get("paciente_id"),
            tabela="atendimentos",
            registro_id=consulta_id,
            acao="UPDATE",
            antes={k: atual.data.get(k) for k in payload.keys()},
            depois={k: result.data[0].get(k) for k in payload.keys()},
        )

        return jsonify(result.data[0]), 200
    except Exception as e:
        return tratar_erro(e)


@consultas_bp.route("/<consulta_id>", methods=["DELETE"])
def cancelar_consulta(consulta_id):
    token = get_token(request)
    if not token:
        return jsonify({"error": "Não autorizado"}), 401

    try:
        ctx = get_contexto(token)
        exigir_permissao(ctx, "cancelar_consultas")
        clinica_id = exigir_clinica(ctx)
        user_id = ctx["user_id"]
        atual = (
            supabase.table("atendimentos")
            .select("*")
            .eq("id", consulta_id)
            .eq("clinica_id", clinica_id)
            .maybe_single()
            .execute()
        )
        if not (atual and atual.data):
            return jsonify({"error": "Atendimento não encontrado"}), 404

        supabase.table("atendimentos").update({
            "status": "Cancelado",
            "updated_by": user_id,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", consulta_id).eq("clinica_id", clinica_id).execute()

        registrar_alteracao(
            clinica_id=clinica_id,
            usuario_id=user_id,
            paciente_id=atual.data.get("paciente_id"),
            tabela="atendimentos",
            registro_id=consulta_id,
            acao="UPDATE",
            antes={"status": atual.data.get("status")},
            depois={"status": "Cancelado"},
        )

        return jsonify({"message": "Consulta cancelada"}), 200
    except Exception as e:
        return tratar_erro(e)

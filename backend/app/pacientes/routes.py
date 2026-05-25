from datetime import datetime, timezone
from flask import Blueprint, request, jsonify
from app.database import supabase
from app.auditoria import registrar_alteracao
from app.validators import (
    campo_obrigatorio,
    validar_cpf,
    validar_telefone,
    validar_data_nascimento,
    validar_email,
)

pacientes_bp = Blueprint("pacientes", __name__)

# Campos que o cliente pode editar via PUT (impede alteração de id/clinica_id/etc.)
CAMPOS_EDITAVEIS = {
    "nome", "cpf", "rg", "data_nascimento", "genero",
    "telefone_whatsapp", "email", "endereco", "anamnese", "odontograma", "status",
}

# Campos da anamnese que precisam estar declarados (mesmo que "Nega").
# Em odonto, anestesiar sem alergia documentada é negligência — bloqueamos no cadastro.
ANAMNESE_OBRIGATORIA = ["alergias", "medicacoes", "condicoes"]


def get_token(req):
    return req.headers.get("Authorization", "").replace("Bearer ", "")


def get_user_clinica(token):
    """Retorna (user_id, clinica_id) do usuário autenticado.

    Se o perfil não existir na tabela usuarios, devolve clinica_id=None e cabe
    à rota decidir como responder. Não recriamos clínica nem perfil silenciosamente.
    """
    user = supabase.auth.get_user(token).user
    perfil = supabase.table("usuarios").select("clinica_id").eq("id", user.id).execute()
    if not perfil.data:
        return user.id, None
    return user.id, perfil.data[0]["clinica_id"]


def _validar_anamnese(anamnese, exigir_obrigatorios=False):
    """Valida o dict de anamnese. Quando exigir_obrigatorios=True, força os campos críticos."""
    if anamnese is None:
        anamnese = {}
    if not isinstance(anamnese, dict):
        raise ValueError("Anamnese deve ser um objeto.")

    if exigir_obrigatorios:
        faltantes = [c for c in ANAMNESE_OBRIGATORIA if not str(anamnese.get(c) or "").strip()]
        if faltantes:
            nomes = {"alergias": "Alergias", "medicacoes": "Medicações em uso", "condicoes": "Condições sistêmicas"}
            lista = ", ".join(nomes[c] for c in faltantes)
            raise ValueError(
                f'Anamnese incompleta. Preencha: {lista}. Se não houver, escreva "Nega" / "Nenhuma".'
            )

    # Campos booleanos opcionais — mas se vierem, têm que ser booleanos.
    for chave in ("usa_anticoagulante", "gestante"):
        if chave in anamnese and not isinstance(anamnese[chave], bool):
            raise ValueError(f"O campo '{chave}' deve ser true ou false.")

    return anamnese


@pacientes_bp.route("/", methods=["GET"])
def listar_pacientes():
    token = get_token(request)
    if not token:
        return jsonify({"error": "Não autorizado"}), 401

    try:
        _, clinica_id = get_user_clinica(token)
        if not clinica_id:
            return jsonify([]), 200
        result = supabase.table("pacientes").select("*").eq("clinica_id", clinica_id).order("created_at", desc=True).execute()
        return jsonify(result.data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@pacientes_bp.route("/<paciente_id>", methods=["GET"])
def obter_paciente(paciente_id):
    token = get_token(request)
    if not token:
        return jsonify({"error": "Não autorizado"}), 401

    try:
        _, clinica_id = get_user_clinica(token)
        if not clinica_id:
            return jsonify({"error": "Paciente não encontrado"}), 404
        result = supabase.table("pacientes").select("*").eq("id", paciente_id).eq("clinica_id", clinica_id).single().execute()
        return jsonify(result.data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@pacientes_bp.route("/", methods=["POST"])
def criar_paciente():
    token = get_token(request)
    if not token:
        return jsonify({"error": "Não autorizado"}), 401

    try:
        user_id, clinica_id = get_user_clinica(token)
        if not clinica_id:
            return jsonify({"error": "Perfil sem clínica vinculada. Contate o proprietário."}), 403
        data = request.get_json() or {}

        try:
            campo_obrigatorio(data.get("nome"), "nome")
            cpf = validar_cpf(data.get("cpf"))
            telefone = validar_telefone(data.get("telefone_whatsapp"))
            data_nascimento = validar_data_nascimento(data.get("data_nascimento"))
            email = data.get("email")
            if email:
                email = validar_email(email)
            anamnese = _validar_anamnese(data.get("anamnese"), exigir_obrigatorios=True)
        except ValueError as e:
            return jsonify({"error": str(e)}), 400

        novo = {
            "clinica_id": clinica_id,
            "nome": data.get("nome"),
            "email": email,
            "telefone_whatsapp": telefone,
            "data_nascimento": data_nascimento,
            "cpf": cpf,
            "rg": data.get("rg"),
            "genero": data.get("genero"),
            "endereco": data.get("endereco", {}),
            "anamnese": anamnese,
            "updated_by": user_id,
        }

        result = supabase.table("pacientes").insert(novo).execute()
        criado = result.data[0]

        registrar_alteracao(
            clinica_id=clinica_id,
            usuario_id=user_id,
            paciente_id=criado["id"],
            tabela="pacientes",
            registro_id=criado["id"],
            acao="INSERT",
            depois=criado,
        )

        return jsonify(criado), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@pacientes_bp.route("/<paciente_id>", methods=["PUT"])
def atualizar_paciente(paciente_id):
    token = get_token(request)
    if not token:
        return jsonify({"error": "Não autorizado"}), 401

    try:
        user_id, clinica_id = get_user_clinica(token)
        if not clinica_id:
            return jsonify({"error": "Paciente não encontrado"}), 404
        data = request.get_json() or {}

        # Mantém apenas os campos que o cliente pode editar
        payload = {k: v for k, v in data.items() if k in CAMPOS_EDITAVEIS}

        if not payload:
            return jsonify({"error": "Nenhum campo válido para atualizar"}), 400

        try:
            if "nome" in payload:
                campo_obrigatorio(payload.get("nome"), "nome")
            if "cpf" in payload:
                payload["cpf"] = validar_cpf(payload.get("cpf"))
            if "telefone_whatsapp" in payload:
                payload["telefone_whatsapp"] = validar_telefone(payload.get("telefone_whatsapp"))
            if "data_nascimento" in payload:
                payload["data_nascimento"] = validar_data_nascimento(payload.get("data_nascimento"))
            if "email" in payload and payload.get("email"):
                payload["email"] = validar_email(payload.get("email"))
            if "anamnese" in payload:
                # No update não exigimos os obrigatórios — paciente pode estar só corrigindo um campo.
                payload["anamnese"] = _validar_anamnese(payload.get("anamnese"), exigir_obrigatorios=False)
        except ValueError as e:
            return jsonify({"error": str(e)}), 400

        # Snapshot antes da alteração — base para a auditoria
        atual = (
            supabase.table("pacientes")
            .select("*")
            .eq("id", paciente_id)
            .eq("clinica_id", clinica_id)
            .single()
            .execute()
        )
        if not atual.data:
            return jsonify({"error": "Paciente não encontrado"}), 404

        payload["updated_by"] = user_id
        payload["updated_at"] = datetime.now(timezone.utc).isoformat()

        result = (
            supabase.table("pacientes")
            .update(payload)
            .eq("id", paciente_id)
            .eq("clinica_id", clinica_id)
            .execute()
        )
        atualizado = result.data[0]

        registrar_alteracao(
            clinica_id=clinica_id,
            usuario_id=user_id,
            paciente_id=paciente_id,
            tabela="pacientes",
            registro_id=paciente_id,
            acao="UPDATE",
            antes={k: atual.data.get(k) for k in payload.keys()},
            depois={k: atualizado.get(k) for k in payload.keys()},
        )

        return jsonify(atualizado), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@pacientes_bp.route("/<paciente_id>", methods=["DELETE"])
def deletar_paciente(paciente_id):
    token = get_token(request)
    if not token:
        return jsonify({"error": "Não autorizado"}), 401

    try:
        user_id, clinica_id = get_user_clinica(token)
        if not clinica_id:
            return jsonify({"error": "Paciente não encontrado"}), 404

        atual = (
            supabase.table("pacientes")
            .select("*")
            .eq("id", paciente_id)
            .eq("clinica_id", clinica_id)
            .single()
            .execute()
        )
        if not atual.data:
            return jsonify({"error": "Paciente não encontrado"}), 404

        supabase.table("pacientes").delete().eq("id", paciente_id).eq("clinica_id", clinica_id).execute()

        registrar_alteracao(
            clinica_id=clinica_id,
            usuario_id=user_id,
            paciente_id=paciente_id,
            tabela="pacientes",
            registro_id=paciente_id,
            acao="DELETE",
            antes=atual.data,
        )

        return jsonify({"message": "Paciente removido"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

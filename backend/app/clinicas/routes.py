from flask import Blueprint, request, jsonify
from app.database import supabase
from app.validators import campo_obrigatorio, validar_cnpj

clinicas_bp = Blueprint("clinicas", __name__)

# Colunas reais da tabela 'clinicas' que o cliente pode gravar.
# Obs.: o frontend envia "nome" — ele é mapeado para "nome_fantasia" abaixo.
COLUNAS_CLINICA = {
    "nome_fantasia", "razao_social", "cnpj", "telefone", "endereco",
}

# Colunas garantidas mesmo sem a migração migration_atualizacoes.sql
COLUNAS_CLINICA_BASICAS = {"nome_fantasia", "razao_social", "cnpj"}


def get_token(req):
    return req.headers.get("Authorization", "").replace("Bearer ", "")


def gravar_clinica(operacao, payload, clinica_id=None):
    """
    Executa insert/update na tabela clinicas. Se as colunas telefone/endereco
    ainda não existirem (migração não aplicada), refaz a operação só com as
    colunas básicas em vez de quebrar.
    """
    def _exec(p):
        if operacao == "insert":
            return supabase.table("clinicas").insert(p).execute()
        return supabase.table("clinicas").update(p).eq("id", clinica_id).execute()

    try:
        return _exec(payload)
    except Exception as e:
        if "Could not find" in str(e):
            basico = {k: v for k, v in payload.items()
                      if k in COLUNAS_CLINICA_BASICAS or k == "dono_id"}
            return _exec(basico)
        raise

def get_user_clinica_id(token):
    """Resolve o clinica_id do usuário autenticado a partir do token."""
    user_response = supabase.auth.get_user(token)
    user_id = user_response.user.id
    perfil = supabase.table("usuarios").select("clinica_id").eq("id", user_id).single().execute()
    return perfil.data.get("clinica_id") if perfil.data else None

@clinicas_bp.route("/", methods=["POST"])
def criar_clinica():
    token = get_token(request)
    if not token:
        return jsonify({"error": "Não autorizado"}), 401

    try:
        user_response = supabase.auth.get_user(token)
        user_id = user_response.user.id
        
        data = request.get_json() or {}

        # O frontend envia "nome"; a coluna real da tabela é "nome_fantasia".
        if data.get("nome") and not data.get("nome_fantasia"):
            data["nome_fantasia"] = data["nome"]

        try:
            campo_obrigatorio(data.get("nome_fantasia"), "nome")
            if data.get("cnpj"):
                data["cnpj"] = validar_cnpj(data.get("cnpj"))
        except ValueError as e:
            return jsonify({"error": str(e)}), 400

        # 1. Monta o payload só com colunas reais e grava a clínica
        payload = {k: v for k, v in data.items() if k in COLUNAS_CLINICA}
        payload["dono_id"] = user_id

        result_clinica = gravar_clinica("insert", payload)
        nova_clinica_id = result_clinica.data[0]["id"]
        
        # 2. Update the user's profile to link the new clinic
        supabase.table("usuarios").update({"clinica_id": nova_clinica_id}).eq("id", user_id).execute()

        return jsonify(result_clinica.data[0]), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@clinicas_bp.route("/", methods=["GET"])
def listar_clinicas():
    """Retorna a clínica do usuário autenticado."""
    token = get_token(request)
    if not token:
        return jsonify({"error": "Não autorizado"}), 401

    try:
        user_response = supabase.auth.get_user(token)
        user_id = user_response.user.id

        perfil = supabase.table("usuarios").select("clinica_id").eq("id", user_id).single().execute()
        clinica_id = perfil.data.get("clinica_id") if perfil.data else None

        if not clinica_id:
            return jsonify([]), 200

        result = supabase.table("clinicas").select("*").eq("id", clinica_id).execute()
        clinicas = result.data or []
        # Expõe "nome" (alias de nome_fantasia) para o frontend usar de forma consistente
        for c in clinicas:
            c["nome"] = c.get("nome_fantasia")
        return jsonify(clinicas), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@clinicas_bp.route("/<clinica_id>", methods=["GET"])
def get_clinica(clinica_id):
    token = get_token(request)
    if not token:
        return jsonify({"error": "Não autorizado"}), 401

    try:
        user_clinica_id = get_user_clinica_id(token)
        if user_clinica_id != clinica_id:
            return jsonify({"error": "Você não tem permissão para acessar esta clínica"}), 403

        result = supabase.table("clinicas").select("*").eq("id", clinica_id).single().execute()
        clinica = result.data or {}
        if clinica:
            clinica["nome"] = clinica.get("nome_fantasia")
        return jsonify(clinica), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@clinicas_bp.route("/<clinica_id>", methods=["PUT"])
def atualizar_clinica(clinica_id):
    token = get_token(request)
    if not token:
        return jsonify({"error": "Não autorizado"}), 401

    try:
        user_clinica_id = get_user_clinica_id(token)
        if user_clinica_id != clinica_id:
            return jsonify({"error": "Você não tem permissão para atualizar esta clínica"}), 403

        data = request.get_json() or {}

        # O frontend envia "nome"; a coluna real da tabela é "nome_fantasia".
        if data.get("nome") and not data.get("nome_fantasia"):
            data["nome_fantasia"] = data["nome"]

        # Mantém apenas as colunas reais da tabela
        payload = {k: v for k, v in data.items() if k in COLUNAS_CLINICA}

        if not payload:
            return jsonify({"error": "Nenhum campo válido para atualizar"}), 400

        try:
            if "nome_fantasia" in payload:
                campo_obrigatorio(payload.get("nome_fantasia"), "nome")
            if "cnpj" in payload and payload.get("cnpj"):
                payload["cnpj"] = validar_cnpj(payload.get("cnpj"))
        except ValueError as e:
            return jsonify({"error": str(e)}), 400

        result = gravar_clinica("update", payload, clinica_id)
        return jsonify(result.data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

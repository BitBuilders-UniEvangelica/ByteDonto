from flask import Blueprint, request, jsonify
from app.database import supabase
from app.validators import campo_obrigatorio, validar_cnpj
from app.auth_utils import get_token, tratar_erro

clinicas_bp = Blueprint("clinicas", __name__)

# Colunas reais da tabela 'clinicas' que o cliente pode gravar.
# Obs.: o frontend envia "nome" — ele é mapeado para "nome_fantasia" abaixo.
# 'resumo' e 'redes_sociais' dependem de migration_atualizacoes.sql; se ainda não
# existirem, gravar_clinica degrada para as colunas básicas em vez de quebrar.
COLUNAS_CLINICA = {
    "nome_fantasia", "razao_social", "cnpj", "telefone", "endereco",
    "resumo", "redes_sociais",
}

# Colunas garantidas mesmo sem a migração migration_atualizacoes.sql
COLUNAS_CLINICA_BASICAS = {"nome_fantasia", "razao_social", "cnpj"}


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

def get_user_id(token):
    """Resolve o id do usuário autenticado a partir do token."""
    return supabase.auth.get_user(token).user.id


def get_user_clinica_id(token):
    """Resolve a clínica ATIVA do usuário autenticado (usuarios.clinica_id)."""
    user_id = get_user_id(token)
    perfil = supabase.table("usuarios").select("clinica_id").eq("id", user_id).maybe_single().execute()
    return perfil.data.get("clinica_id") if (perfil and perfil.data) else None


def pode_acessar_clinica(user_id, clinica_id):
    """
    Autoriza o usuário a ver/editar uma clínica se ele for o DONO dela
    (clinicas.dono_id) ou se for a sua clínica ativa (usuarios.clinica_id).
    Permite que o dono acesse qualquer uma das várias clínicas que possui,
    não apenas a ativa.
    """
    clinica = supabase.table("clinicas").select("dono_id").eq("id", clinica_id).maybe_single().execute()
    if clinica and clinica.data and clinica.data.get("dono_id") == user_id:
        return True
    perfil = supabase.table("usuarios").select("clinica_id").eq("id", user_id).maybe_single().execute()
    return bool(perfil and perfil.data and perfil.data.get("clinica_id") == clinica_id)

@clinicas_bp.route("/", methods=["POST"])
def criar_clinica():
    token = get_token(request)
    if not token:
        return jsonify({"error": "Não autorizado"}), 401

    try:
        user_response = supabase.auth.get_user(token)
        user_id = user_response.user.id
        
        data = request.get_json(silent=True) or {}

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

        # 2. A clínica recém-criada vira a clínica ATIVA do dono. As clínicas
        #    anteriores continuam vinculadas via clinicas.dono_id (não se perdem).
        supabase.table("usuarios").update({"clinica_id": nova_clinica_id}).eq("id", user_id).execute()

        return jsonify(result_clinica.data[0]), 201
    except Exception as e:
        return tratar_erro(e)

@clinicas_bp.route("/", methods=["GET"])
def listar_clinicas():
    """
    Lista TODAS as clínicas do dono autenticado (clinicas.dono_id), não apenas
    a clínica ativa. Cada item recebe `ativa: true/false` indicando qual é a
    clínica ativa no momento (usuarios.clinica_id). Para um membro que não é
    dono de nenhuma clínica, retorna apenas a sua clínica ativa.
    """
    token = get_token(request)
    if not token:
        return jsonify({"error": "Não autorizado"}), 401

    try:
        user_id = get_user_id(token)

        perfil = supabase.table("usuarios").select("clinica_id").eq("id", user_id).maybe_single().execute()
        clinica_ativa_id = perfil.data.get("clinica_id") if (perfil and perfil.data) else None

        # Clínicas que o usuário possui (é dono)
        result = (
            supabase.table("clinicas")
            .select("*")
            .eq("dono_id", user_id)
            .order("created_at")
            .execute()
        )
        clinicas = result.data or []

        # Membro sem clínicas próprias: cai de volta para a clínica ativa
        if not clinicas and clinica_ativa_id:
            fallback = supabase.table("clinicas").select("*").eq("id", clinica_ativa_id).execute()
            clinicas = fallback.data or []

        for c in clinicas:
            c["nome"] = c.get("nome_fantasia")
            c["ativa"] = c.get("id") == clinica_ativa_id
        return jsonify(clinicas), 200
    except Exception as e:
        return tratar_erro(e)


@clinicas_bp.route("/<clinica_id>/ativar", methods=["PUT"])
def ativar_clinica(clinica_id):
    """Define a clínica indicada como a clínica ativa do dono autenticado."""
    token = get_token(request)
    if not token:
        return jsonify({"error": "Não autorizado"}), 401

    try:
        user_id = get_user_id(token)

        clinica = supabase.table("clinicas").select("dono_id").eq("id", clinica_id).maybe_single().execute()
        if not (clinica and clinica.data):
            return jsonify({"error": "Clínica não encontrada"}), 404
        if clinica.data.get("dono_id") != user_id:
            return jsonify({"error": "Você não é o dono desta clínica"}), 403

        supabase.table("usuarios").update({"clinica_id": clinica_id}).eq("id", user_id).execute()
        return jsonify({"ok": True, "clinica_id": clinica_id}), 200
    except Exception as e:
        return tratar_erro(e)


@clinicas_bp.route("/<clinica_id>", methods=["GET"])
def get_clinica(clinica_id):
    token = get_token(request)
    if not token:
        return jsonify({"error": "Não autorizado"}), 401

    try:
        user_id = get_user_id(token)
        if not pode_acessar_clinica(user_id, clinica_id):
            return jsonify({"error": "Você não tem permissão para acessar esta clínica"}), 403

        result = supabase.table("clinicas").select("*").eq("id", clinica_id).maybe_single().execute()
        clinica = (result.data if result else None) or {}
        if not clinica:
            return jsonify({"error": "Clínica não encontrada"}), 404
        clinica["nome"] = clinica.get("nome_fantasia")
        return jsonify(clinica), 200
    except Exception as e:
        return tratar_erro(e)

@clinicas_bp.route("/<clinica_id>", methods=["PUT"])
def atualizar_clinica(clinica_id):
    token = get_token(request)
    if not token:
        return jsonify({"error": "Não autorizado"}), 401

    try:
        user_id = get_user_id(token)
        if not pode_acessar_clinica(user_id, clinica_id):
            return jsonify({"error": "Você não tem permissão para atualizar esta clínica"}), 403

        data = request.get_json(silent=True) or {}

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
        return tratar_erro(e)

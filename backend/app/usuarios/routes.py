from flask import Blueprint, request, jsonify
from supabase import create_client
from app.database import supabase
from config import Config

supabase_admin = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)

usuarios_bp = Blueprint("usuarios", __name__)

PERMISSOES_PADRAO = {
    "Especialista": {
        "ver_pacientes":      True,
        "editar_pacientes":   False,
        "ver_prontuario":     True,
        "editar_prontuario":  True,
        "ver_agenda":         True,
        "agendar_consultas":  False,
        "cancelar_consultas": False,
        "ver_financeiro":     False,
    },
    "Recepção": {
        "ver_pacientes":      True,
        "editar_pacientes":   True,
        "ver_prontuario":     False,
        "editar_prontuario":  False,
        "ver_agenda":         True,
        "agendar_consultas":  True,
        "cancelar_consultas": True,
        "ver_financeiro":     True,
    },
}


def get_token(req):
    return req.headers.get("Authorization", "").replace("Bearer ", "")


def get_user_e_clinica(token):
    user = supabase.auth.get_user(token).user
    perfil = supabase.table("usuarios").select("clinica_id, papel").eq("id", user.id).single().execute()
    return user.id, perfil.data["clinica_id"], perfil.data["papel"]


@usuarios_bp.route("/", methods=["GET"])
def listar_equipe():
    """Lista todos os membros da clínica do proprietário autenticado."""
    token = get_token(request)
    if not token:
        return jsonify({"error": "Não autorizado"}), 401

    try:
        _, clinica_id, _ = get_user_e_clinica(token)

        # select("*") — robusto: funciona com ou sem a coluna 'ativo'
        result = (
            supabase.table("usuarios")
            .select("*")
            .eq("clinica_id", clinica_id)
            .order("created_at")
            .execute()
        )
        return jsonify(result.data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@usuarios_bp.route("/criar", methods=["POST"])
def criar_membro():
    """
    Proprietário cria conta para um membro da equipe.
    Body: { nome, email, senha, papel }
    Papéis válidos: 'Especialista', 'Recepção'
    """
    token = get_token(request)
    if not token:
        return jsonify({"error": "Não autorizado"}), 401

    try:
        _, clinica_id, papel_solicitante = get_user_e_clinica(token)

        if papel_solicitante != "Dono":
            return jsonify({"error": "Apenas o proprietário pode criar membros"}), 403

        data = request.get_json()
        nome = data.get("nome", "").strip()
        email = data.get("email", "").strip()
        senha = data.get("senha", "").strip()
        papel = data.get("papel", "").strip()

        if not all([nome, email, senha, papel]):
            return jsonify({"error": "Nome, email, senha e papel são obrigatórios"}), 400

        if papel not in ["Especialista", "Recepção"]:
            return jsonify({"error": "Papel inválido. Use 'Especialista' ou 'Recepção'"}), 400

        if len(senha) < 6:
            return jsonify({"error": "A senha deve ter no mínimo 6 caracteres"}), 400

        # Cria o usuário no Supabase Auth usando a service role key
        auth_response = supabase_admin.auth.admin.create_user({
            "email": email,
            "password": senha,
            "email_confirm": True  # Confirma o email automaticamente
        })

        novo_usuario_id = auth_response.user.id

        # Cria o perfil na tabela usuarios vinculado à clínica.
        # 'ativo' não é enviado: a coluna tem default TRUE, então a criação
        # funciona mesmo se a migração 'ativo' ainda não tiver sido aplicada.
        supabase_admin.table("usuarios").insert({
            "id": novo_usuario_id,
            "clinica_id": clinica_id,
            "nome": nome,
            "papel": papel,
            "permissoes": PERMISSOES_PADRAO.get(papel, {}),
        }).execute()

        return jsonify({
            "message": f"Membro '{nome}' criado com sucesso",
            "id": novo_usuario_id,
            "nome": nome,
            "email": email,
            "papel": papel,
        }), 201

    except Exception as e:
        error_msg = str(e)
        if "already been registered" in error_msg or "already registered" in error_msg:
            return jsonify({"error": "Este e-mail já está cadastrado no sistema"}), 409
        return jsonify({"error": error_msg}), 500


@usuarios_bp.route("/<usuario_id>", methods=["DELETE"])
def remover_membro(usuario_id):
    """
    Proprietário remove um membro da equipe.
    Deleta o perfil da tabela e o usuário do Auth.
    """
    token = get_token(request)
    if not token:
        return jsonify({"error": "Não autorizado"}), 401

    try:
        solicitante_id, clinica_id, papel_solicitante = get_user_e_clinica(token)

        if papel_solicitante != "Dono":
            return jsonify({"error": "Apenas o proprietário pode remover membros"}), 403

        if usuario_id == solicitante_id:
            return jsonify({"error": "Você não pode remover a si mesmo"}), 400

        # Verifica se o membro pertence à mesma clínica
        membro = supabase.table("usuarios").select("clinica_id, papel").eq("id", usuario_id).single().execute()
        if not membro.data or membro.data["clinica_id"] != clinica_id:
            return jsonify({"error": "Membro não encontrado nesta clínica"}), 404

        if membro.data["papel"] == "Dono":
            return jsonify({"error": "Não é possível remover outro proprietário"}), 403

        # Remove o perfil da tabela usuarios
        supabase_admin.table("usuarios").delete().eq("id", usuario_id).execute()

        # Remove o usuário do Auth
        supabase_admin.auth.admin.delete_user(usuario_id)

        return jsonify({"message": "Membro removido com sucesso"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@usuarios_bp.route("/<usuario_id>", methods=["PUT"])
def atualizar_membro(usuario_id):
    """Proprietário atualiza nome ou papel de um membro."""
    token = get_token(request)
    if not token:
        return jsonify({"error": "Não autorizado"}), 401

    try:
        _, clinica_id, papel_solicitante = get_user_e_clinica(token)

        if papel_solicitante != "Dono":
            return jsonify({"error": "Apenas o proprietário pode editar membros"}), 403

        membro = supabase.table("usuarios").select("clinica_id, papel").eq("id", usuario_id).single().execute()
        if not membro.data or membro.data["clinica_id"] != clinica_id:
            return jsonify({"error": "Membro não encontrado nesta clínica"}), 404

        data = request.get_json()
        atualizacao = {}
        if "nome" in data:
            atualizacao["nome"] = data["nome"].strip()
        if "papel" in data and data["papel"] in ["Especialista", "Recepção"]:
            atualizacao["papel"] = data["papel"]
        if "percentual_repasse" in data:
            try:
                pct = float(data["percentual_repasse"])
            except (TypeError, ValueError):
                return jsonify({"error": "Percentual de repasse deve ser um número."}), 400
            if pct < 0 or pct > 100:
                return jsonify({"error": "Percentual de repasse deve estar entre 0 e 100."}), 400
            atualizacao["percentual_repasse"] = pct
        if "ativo" in data:
            valor = data["ativo"]
            if isinstance(valor, bool):
                ativo = valor
            elif isinstance(valor, str):
                if valor.strip().lower() in ("true", "1"):
                    ativo = True
                elif valor.strip().lower() in ("false", "0"):
                    ativo = False
                else:
                    return jsonify({"error": "O campo 'ativo' deve ser um booleano"}), 400
            elif isinstance(valor, (int,)):
                ativo = bool(valor)
            else:
                return jsonify({"error": "O campo 'ativo' deve ser um booleano"}), 400

            if ativo is False and membro.data.get("papel") == "Dono":
                return jsonify({"error": "Não é possível desativar o acesso de um proprietário"}), 400
            atualizacao["ativo"] = ativo

        if not atualizacao:
            return jsonify({"error": "Nenhum campo válido para atualizar"}), 400

        result = supabase_admin.table("usuarios").update(atualizacao).eq("id", usuario_id).execute()
        return jsonify(result.data[0]), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@usuarios_bp.route("/<usuario_id>/permissoes", methods=["GET"])
def get_permissoes(usuario_id):
    """Retorna as permissões de um membro. Acessível pelo Dono."""
    token = get_token(request)
    if not token:
        return jsonify({"error": "Não autorizado"}), 401

    try:
        _, clinica_id, papel_solicitante = get_user_e_clinica(token)

        if papel_solicitante != "Dono":
            return jsonify({"error": "Apenas o proprietário pode ver permissões"}), 403

        membro = (
            supabase.table("usuarios")
            .select("id, nome, papel, permissoes")
            .eq("id", usuario_id)
            .eq("clinica_id", clinica_id)
            .single()
            .execute()
        )
        if not membro.data:
            return jsonify({"error": "Membro não encontrado"}), 404

        return jsonify(membro.data), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@usuarios_bp.route("/<usuario_id>/permissoes", methods=["PATCH"])
def atualizar_permissoes(usuario_id):
    """
    Proprietário atualiza permissões individuais de um membro.
    Body: { "permissoes": { "ver_financeiro": true, ... } }
    Faz merge das chaves enviadas com as permissões existentes.
    """
    token = get_token(request)
    if not token:
        return jsonify({"error": "Não autorizado"}), 401

    try:
        _, clinica_id, papel_solicitante = get_user_e_clinica(token)

        if papel_solicitante != "Dono":
            return jsonify({"error": "Apenas o proprietário pode alterar permissões"}), 403

        membro = (
            supabase.table("usuarios")
            .select("clinica_id, papel, permissoes")
            .eq("id", usuario_id)
            .single()
            .execute()
        )
        if not membro.data or membro.data["clinica_id"] != clinica_id:
            return jsonify({"error": "Membro não encontrado nesta clínica"}), 404

        if membro.data["papel"] == "Dono":
            return jsonify({"error": "Permissões do proprietário não podem ser alteradas"}), 403

        data = request.get_json()
        novas = data.get("permissoes")
        if not isinstance(novas, dict):
            return jsonify({"error": "Campo 'permissoes' deve ser um objeto"}), 400

        chaves_validas = set(PERMISSOES_PADRAO["Especialista"].keys())
        invalidas = set(novas.keys()) - chaves_validas
        if invalidas:
            return jsonify({"error": f"Permissões inválidas: {', '.join(invalidas)}"}), 400

        permissoes_atuais = membro.data.get("permissoes") or {}
        permissoes_merged = {**permissoes_atuais, **novas}

        result = (
            supabase_admin.table("usuarios")
            .update({"permissoes": permissoes_merged})
            .eq("id", usuario_id)
            .execute()
        )
        return jsonify({"permissoes": result.data[0]["permissoes"]}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

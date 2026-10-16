from flask import Blueprint, request, jsonify
from app.database import create_client
from config import Config
from app.database import supabase
from app.extensions import limiter

supabase_auth = create_client(Config.SUPABASE_URL, Config.SUPABASE_ANON_KEY)
supabase_admin = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/registro", methods=["POST"])
@limiter.limit("10 per hour")
def registro():
    """
    Cria conta de proprietário.
    Body: { nome, email, password }
    Cria usuário no Supabase Auth + perfil na tabela usuarios com papel='Dono'.
    A clínica é criada separadamente após o registro.
    """
    data = request.get_json()
    nome = (data.get("nome") or "").strip()
    email = (data.get("email") or "").strip()
    password = (data.get("password") or "").strip()

    if not all([nome, email, password]):
        return jsonify({"error": "Nome, email e senha são obrigatórios"}), 400

    if len(password) < 8:
        return jsonify({"error": "A senha deve ter no mínimo 8 caracteres"}), 400

    try:
        auth_response = supabase_admin.auth.admin.create_user({
            "email": email,
            "password": password,
            "email_confirm": True,
        })

        novo_id = auth_response.user.id

        supabase_admin.table("usuarios").insert({
            "id": novo_id,
            "nome": nome,
            "papel": "Dono",
            "permissoes": {},
        }).execute()

        return jsonify({"message": "Conta criada com sucesso. Faça login para continuar."}), 201

    except Exception as e:
        error_msg = str(e)
        if "already been registered" in error_msg or "already registered" in error_msg:
            return jsonify({"error": "Este e-mail já está cadastrado"}), 409
        return jsonify({"error": error_msg}), 500



@auth_bp.route("/login", methods=["POST"])
@limiter.limit("5 per minute;20 per hour")
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({
            "error": "Email e senha são obrigatórios"
        }), 400

    # 1. Autentica o usuário
    try:
        response = supabase_auth.auth.sign_in_with_password({
            "email": email,
            "password": password,
        })

        user = response.user
        session = response.session

    except Exception:
        return jsonify({"error": "Credenciais inválidas"}), 401

    try:
        # 2. Busca o perfil no banco
        perfil_response = (
            supabase_admin.table("usuarios")
            .select("id, nome, papel, clinica_id, ativo")
            .eq("id", user.id)
            .maybe_single()
            .execute()
        )

        perfil = perfil_response.data

        if not perfil:
            return jsonify({
                "error": "Perfil do usuário não encontrado na tabela usuarios."
            }), 404

        if perfil.get("ativo") is False:
            return jsonify({
                "error": "Seu acesso foi desativado."
            }), 403

        clinica_id = perfil.get("clinica_id")

        # 3. Só cria ou recupera uma clínica automaticamente
        # para usuários que sejam proprietários.
        if not clinica_id and perfil.get("papel") == "Dono":

            # Evita duplicação caso a clínica já exista,
            # mas o vínculo com o usuário esteja ausente.
            clinicas_existentes = (
                supabase_admin.table("clinicas")
                .select("id")
                .eq("dono_id", user.id)
                .limit(1)
                .execute()
            )

            if clinicas_existentes.data:
                clinica_id = clinicas_existentes.data[0]["id"]

            else:
                nome_clinica = (
                    f"Clínica de {perfil.get('nome') or user.email}"
                )

                nova_clinica = (
                    supabase_admin.table("clinicas")
                    .insert({
                        "dono_id": user.id,
                        "nome_fantasia": nome_clinica,
                    })
                    .execute()
                )

                if not nova_clinica.data:
                    raise RuntimeError(
                        "Não foi possível criar a clínica."
                    )

                clinica_id = nova_clinica.data[0]["id"]

            # 4. Vincula a clínica ao perfil do proprietário
            supabase_admin.table("usuarios").update({
                "clinica_id": clinica_id
            }).eq("id", user.id).execute()

        return jsonify({
            "access_token": session.access_token,
            "user": {
                "id": user.id,
                "email": user.email,
                "clinica_id": clinica_id,
                "papel": perfil.get("papel"),
            }
        }), 200

    except Exception as e:
        # Não classifica falhas no banco como credenciais inválidas.
        print(f"Erro ao preparar perfil/clínica no login: {e}")

        return jsonify({
            "error": "Não foi possível carregar o perfil ou preparar a clínica."
        }), 500


@auth_bp.route("/logout", methods=["POST"])
def logout():
    """
    Logout — revoga a sessão do usuário no Supabase (invalida os refresh tokens).
    Header: Authorization: Bearer <token>
    """
    token = request.headers.get("Authorization", "").replace("Bearer ", "")

    if not token:
        return jsonify({"error": "Token não fornecido"}), 401

    try:
        # admin.sign_out revoga as sessões do usuário dono deste JWT. Sem isso,
        # o sign_out() do cliente compartilhado não derrubava a sessão real.
        supabase_admin.auth.admin.sign_out(token)
    except Exception:
        # Token já expirado/inválido — do ponto de vista do cliente, é logout ok.
        pass
    return jsonify({"message": "Logout realizado com sucesso"}), 200


@auth_bp.route("/me", methods=["GET"])
def me():
    """
    Retorna dados do usuário autenticado.
    Header: Authorization: Bearer <token>
    """
    token = request.headers.get("Authorization", "").replace("Bearer ", "")

    if not token:
        return jsonify({"error": "Token não fornecido"}), 401

    # Etapa 1: validar o token (falha aqui = problema de autenticação -> 401)
    try:
        user_response = supabase.auth.get_user(token)
        user = user_response.user
    except Exception as e:
        return jsonify({"error": "Token inválido", "detail": str(e)}), 401

    if not user:
        return jsonify({"error": "Token inválido"}), 401

    # Etapa 2: buscar o perfil (falha aqui = problema de banco -> 500, não 401)
    try:
        perfil_response = supabase.table("usuarios").select("*").eq("id", user.id).execute()
        perfil_data = perfil_response.data[0] if perfil_response.data else None
    except Exception as e:
        return jsonify({
            "error": "Erro ao buscar perfil do usuário. Verifique se as tabelas do banco foram criadas.",
            "detail": str(e)
        }), 500

    return jsonify({
        "id": user.id,
        "email": user.email,
        "perfil": perfil_data
    }), 200

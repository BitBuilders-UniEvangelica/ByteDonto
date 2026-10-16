from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
from uuid import uuid4
from app.database import create_client
from app.database import supabase
from app.auth_utils import get_token, get_user_clinica, tratar_erro
from config import Config

imagens_bp = Blueprint("imagens", __name__)

supabase_admin = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)

BUCKET = "paciente-imagens"

# Tempo de validade do link assinado (1 hora) — paciente abre, vê, link expira.
SIGNED_URL_TTL = 60 * 60

EXTENSOES_PERMITIDAS = {"png", "jpg", "jpeg", "webp", "gif", "pdf"}
TAMANHO_MAXIMO_BYTES = 10 * 1024 * 1024  # 10 MB

TIPOS_VALIDOS = {"imagem", "laudo", "termo_consentimento", "termo_lgpd"}


def extensao_permitida(filename):
    if "." not in filename:
        return False
    return filename.rsplit(".", 1)[1].lower() in EXTENSOES_PERMITIDAS


def gerar_signed_url(storage_path):
    """Gera link assinado de leitura curta para o arquivo. Bucket DEVE ser privado."""
    if not storage_path:
        return None
    try:
        resp = supabase_admin.storage.from_(BUCKET).create_signed_url(storage_path, SIGNED_URL_TTL)
        # supabase-py retorna dict com 'signedURL' ou 'signed_url' dependendo da versão
        return resp.get("signedURL") or resp.get("signed_url") or resp.get("signedUrl")
    except Exception:
        return None


@imagens_bp.route("/upload", methods=["POST"])
def upload_imagem():
    token = get_token(request)
    if not token:
        return jsonify({"error": "Nao autorizado"}), 401

    try:
        _, clinica_id = get_user_clinica(token)

        paciente_id = request.form.get("paciente_id")
        if not paciente_id:
            return jsonify({"error": "paciente_id e obrigatorio"}), 400

        tipo = request.form.get("tipo", "imagem")
        if tipo not in TIPOS_VALIDOS:
            tipo = "imagem"

        if "file" not in request.files:
            return jsonify({"error": "Nenhum arquivo enviado"}), 400

        file = request.files["file"]
        if not file.filename:
            return jsonify({"error": "Nome de arquivo invalido"}), 400

        if not extensao_permitida(file.filename):
            return jsonify({
                "error": "Tipo de arquivo não permitido. "
                         "Envie apenas imagens (png, jpg, jpeg, webp, gif) ou PDF."
            }), 400

        # Confirma que o paciente pertence à clínica do usuário
        paciente = (
            supabase.table("pacientes")
            .select("id, clinica_id")
            .eq("id", paciente_id)
            .maybe_single()
            .execute()
        )
        if not (paciente and paciente.data):
            return jsonify({"error": "Paciente não encontrado"}), 404
        if paciente.data.get("clinica_id") != clinica_id:
            return jsonify({"error": "Acesso negado a este paciente"}), 403

        file_bytes = file.read()
        if len(file_bytes) > TAMANHO_MAXIMO_BYTES:
            return jsonify({
                "error": "Arquivo muito grande. O tamanho máximo permitido é 10 MB."
            }), 400

        filename_unico = f"{uuid4().hex}_{secure_filename(file.filename)}"
        storage_path = f"{clinica_id}/{paciente_id}/{filename_unico}"
        content_type = file.content_type or "application/octet-stream"

        supabase_admin.storage.from_(BUCKET).upload(
            storage_path,
            file_bytes,
            {"content-type": content_type},
        )

        # Persistimos apenas o storage_path. A URL pública NÃO é mais armazenada —
        # ela é gerada sob demanda como signed URL para respeitar LGPD (dado sensível de saúde).
        registro = {
            "clinica_id": clinica_id,
            "paciente_id": paciente_id,
            "nome": file.filename,
            "storage_path": storage_path,
            "tipo": tipo,
        }
        result = supabase.table("paciente_imagens").insert(registro).execute()
        imagem = result.data[0]

        return jsonify({
            "id": imagem["id"],
            "nome": imagem["nome"],
            "tipo": imagem.get("tipo"),
            "url": gerar_signed_url(storage_path),
        }), 201
    except Exception as e:
        return tratar_erro(e)


@imagens_bp.route("/", methods=["GET"])
def listar_imagens():
    token = get_token(request)
    if not token:
        return jsonify({"error": "Nao autorizado"}), 401

    paciente_id = request.args.get("paciente_id")
    if not paciente_id:
        return jsonify({"error": "paciente_id e obrigatorio"}), 400

    try:
        _, clinica_id = get_user_clinica(token)

        result = (
            supabase.table("paciente_imagens")
            .select("*")
            .eq("clinica_id", clinica_id)
            .eq("paciente_id", paciente_id)
            .order("created_at", desc=True)
            .execute()
        )

        # Gera URL assinada para cada arquivo na hora de devolver.
        # Link curto (1h) — se o usuário deixar a aba aberta, recarregar refaz.
        imagens = []
        for img in result.data or []:
            imagens.append({
                **img,
                "url": gerar_signed_url(img.get("storage_path")),
            })
        return jsonify(imagens), 200
    except Exception as e:
        return tratar_erro(e)


@imagens_bp.route("/<imagem_id>", methods=["DELETE"])
def deletar_imagem(imagem_id):
    token = get_token(request)
    if not token:
        return jsonify({"error": "Nao autorizado"}), 401

    try:
        _, clinica_id = get_user_clinica(token)

        check = (
            supabase.table("paciente_imagens")
            .select("id, storage_path")
            .eq("id", imagem_id)
            .eq("clinica_id", clinica_id)
            .maybe_single()
            .execute()
        )

        if not (check and check.data):
            return jsonify({"error": "Imagem nao encontrada"}), 404

        storage_path = check.data["storage_path"]

        supabase_admin.storage.from_(BUCKET).remove([storage_path])
        supabase.table("paciente_imagens").delete().eq("id", imagem_id).execute()

        return jsonify({"message": "Imagem deletada com sucesso"}), 200
    except Exception as e:
        return tratar_erro(e)

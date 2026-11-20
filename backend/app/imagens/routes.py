from flask import Blueprint, request, jsonify
from uuid import uuid4
from app.database import supabase, cliente_admin
from app.auditoria import registrar_alteracao
from app.auth_utils import (
    get_token, get_contexto, exigir_clinica, exigir_alguma_permissao,
    tem_permissao, tratar_erro,
)

imagens_bp = Blueprint("imagens", __name__)

supabase_admin = cliente_admin()

BUCKET = "paciente-imagens"

# Tempo de validade do link assinado (1 hora) — paciente abre, vê, link expira.
SIGNED_URL_TTL = 60 * 60

EXTENSOES_PERMITIDAS = {"png", "jpg", "jpeg", "webp", "gif", "pdf"}
TAMANHO_MAXIMO_BYTES = 10 * 1024 * 1024  # 10 MB

TIPOS_VALIDOS = {"imagem", "laudo", "termo_consentimento", "termo_lgpd"}

# RBAC por tipo de arquivo. Imagens clínicas e laudos fazem parte do prontuário;
# termos (LGPD/consentimento) são coletados também pela recepção.
TIPOS_CLINICOS = {"imagem", "laudo"}
PERMISSOES_LEITURA = {
    "clinico": ("ver_prontuario",),
    "termo": ("ver_pacientes", "ver_prontuario"),
}
PERMISSOES_ESCRITA = {
    "clinico": ("editar_prontuario",),
    "termo": ("editar_pacientes", "editar_prontuario"),
}

# MIME real -> extensões compatíveis. O MIME é SEMPRE determinado pelo
# conteúdo do arquivo (magic bytes), nunca pelo Content-Type do cliente.
EXTENSOES_POR_MIME = {
    "image/png": {"png"},
    "image/jpeg": {"jpg", "jpeg"},
    "image/gif": {"gif"},
    "image/webp": {"webp"},
    "application/pdf": {"pdf"},
}


def _categoria(tipo):
    return "clinico" if tipo in TIPOS_CLINICOS else "termo"


def pode_ler_tipo(ctx, tipo):
    return any(tem_permissao(ctx, c) for c in PERMISSOES_LEITURA[_categoria(tipo)])


def exigir_escrita_tipo(ctx, tipo):
    exigir_alguma_permissao(ctx, *PERMISSOES_ESCRITA[_categoria(tipo)])


def extensao_do_arquivo(filename):
    if not filename or "." not in filename:
        return None
    return filename.rsplit(".", 1)[1].lower()


def extensao_permitida(filename):
    return extensao_do_arquivo(filename) in EXTENSOES_PERMITIDAS


def detectar_mime(conteudo):
    """Identifica o tipo real do arquivo pelas assinaturas (magic bytes).

    Retorna o MIME ou None se o conteúdo não for de um formato permitido.
    """
    if not conteudo:
        return None
    if conteudo.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if conteudo.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if conteudo[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    if len(conteudo) >= 12 and conteudo[:4] == b"RIFF" and conteudo[8:12] == b"WEBP":
        return "image/webp"
    # Estrito: exige a assinatura no início (evita arquivos poliglotas).
    if conteudo.startswith(b"%PDF-"):
        return "application/pdf"
    return None


def caminho_confere(registro, clinica_id):
    """O arquivo precisa estar na pasta da clínica e do paciente do registro.

    Defesa em profundidade: mesmo que um registro fosse adulterado no banco para
    apontar para o arquivo de outra clínica, o link não é gerado."""
    caminho = registro.get("storage_path") or ""
    esperado = f"{clinica_id}/{registro.get('paciente_id')}/"
    return caminho.startswith(esperado) and ".." not in caminho


def _auditar(ctx, registro, acao):
    """Operações sensíveis com documentos clínicos (Res. CFO 226/2020 / LGPD).

    Registra metadados (nome, tipo, caminho) — nunca o conteúdo do arquivo."""
    registrar_alteracao(
        clinica_id=ctx["clinica_id"],
        usuario_id=ctx["user_id"],
        paciente_id=registro.get("paciente_id"),
        tabela="paciente_imagens",
        registro_id=registro["id"],
        acao=acao,
        antes={k: registro.get(k) for k in ("nome", "tipo", "storage_path")} if acao == "DELETE" else None,
        depois={k: registro.get(k) for k in ("nome", "tipo", "storage_path")} if acao != "DELETE" else None,
    )


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
        ctx = get_contexto(token)
        clinica_id = exigir_clinica(ctx)

        paciente_id = request.form.get("paciente_id")
        if not paciente_id:
            return jsonify({"error": "paciente_id e obrigatorio"}), 400

        tipo = request.form.get("tipo", "imagem")
        if tipo not in TIPOS_VALIDOS:
            tipo = "imagem"

        exigir_escrita_tipo(ctx, tipo)

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

        # Lê no máximo 1 byte além do limite: basta para saber se estourou.
        file_bytes = file.read(TAMANHO_MAXIMO_BYTES + 1)
        if len(file_bytes) > TAMANHO_MAXIMO_BYTES:
            return jsonify({
                "error": "Arquivo muito grande. O tamanho máximo permitido é 10 MB."
            }), 400
        if not file_bytes:
            return jsonify({"error": "Arquivo vazio."}), 400

        # Conteúdo real (magic bytes) tem que ser de um formato permitido E
        # compatível com a extensão informada. O Content-Type do cliente é ignorado.
        content_type = detectar_mime(file_bytes)
        extensao = extensao_do_arquivo(file.filename)
        if not content_type or extensao not in EXTENSOES_POR_MIME[content_type]:
            return jsonify({
                "error": "O conteúdo do arquivo não corresponde a uma imagem "
                         "(png, jpg, jpeg, webp, gif) ou PDF válido."
            }), 400

        # Nome no storage gerado pelo servidor: único e sem nada vindo do cliente.
        storage_path = f"{clinica_id}/{paciente_id}/{uuid4().hex}.{extensao}"

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
        _auditar(ctx, imagem, "INSERT")

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
        ctx = get_contexto(token)
        exigir_alguma_permissao(ctx, "ver_pacientes", "ver_prontuario")
        clinica_id = ctx["clinica_id"]
        if not clinica_id:
            return jsonify([]), 200

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
            # Sem acesso ao prontuário: só os termos (LGPD/consentimento).
            if not pode_ler_tipo(ctx, img.get("tipo") or "imagem"):
                continue
            if not caminho_confere(img, clinica_id):
                continue
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
        ctx = get_contexto(token)
        clinica_id = exigir_clinica(ctx)

        check = (
            supabase.table("paciente_imagens")
            .select("id, paciente_id, nome, storage_path, tipo")
            .eq("id", imagem_id)
            .eq("clinica_id", clinica_id)
            .maybe_single()
            .execute()
        )

        if not (check and check.data):
            return jsonify({"error": "Imagem nao encontrada"}), 404

        exigir_escrita_tipo(ctx, check.data.get("tipo") or "imagem")

        storage_path = check.data["storage_path"]

        supabase_admin.storage.from_(BUCKET).remove([storage_path])
        supabase.table("paciente_imagens").delete().eq("id", imagem_id).eq("clinica_id", clinica_id).execute()
        _auditar(ctx, check.data, "DELETE")

        return jsonify({"message": "Imagem deletada com sucesso"}), 200
    except Exception as e:
        return tratar_erro(e)


@imagens_bp.route("/<imagem_id>/download", methods=["GET"])
def link_de_download(imagem_id):
    """Gera um link assinado NOVO (1 h) para um documento, depois de conferir:
    autenticação, clínica, paciente, permissão de leitura do tipo do documento e
    o caminho no storage. O acesso é registrado na auditoria."""
    token = get_token(request)
    if not token:
        return jsonify({"error": "Nao autorizado"}), 401

    try:
        ctx = get_contexto(token)
        clinica_id = exigir_clinica(ctx)
        res = (
            supabase.table("paciente_imagens")
            .select("id, paciente_id, nome, storage_path, tipo")
            .eq("id", imagem_id)
            .eq("clinica_id", clinica_id)
            .maybe_single()
            .execute()
        )
        registro = res.data if res else None
        if not registro:
            return jsonify({"error": "Imagem nao encontrada"}), 404
        if not pode_ler_tipo(ctx, registro.get("tipo") or "imagem"):
            return jsonify({"error": "Você não tem permissão para esta ação."}), 403
        if not caminho_confere(registro, clinica_id):
            return jsonify({"error": "Imagem nao encontrada"}), 404

        url = gerar_signed_url(registro["storage_path"])
        if not url:
            return jsonify({"error": "Arquivo indisponível no armazenamento."}), 404
        _auditar(ctx, registro, "ACESSO")
        return jsonify({"id": registro["id"], "nome": registro["nome"], "tipo": registro.get("tipo"),
                        "url": url, "expira_em_segundos": SIGNED_URL_TTL}), 200
    except Exception as e:
        return tratar_erro(e)

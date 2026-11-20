import re
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify
from app.database import supabase
from app.auditoria import registrar_alteracao
from app.horarios import para_saida
from app.paginacao import ler_paginacao, buscar_pagina, envelope
from app.validators import (
    campo_obrigatorio,
    validar_cpf,
    validar_telefone,
    validar_data_nascimento,
    validar_email,
)
from app.auth_utils import (
    get_token, get_contexto, tem_permissao, exigir_permissao,
    exigir_alguma_permissao, exigir_papel, tratar_erro,
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

# Campos clínicos do prontuário: o odontograma só é visível/editável por quem
# tem acesso ao prontuário. A anamnese é coletada pela recepção no cadastro,
# então pode ser editada por quem edita pacientes OU por quem edita prontuário.
CAMPOS_PRONTUARIO = {"odontograma"}

# Colunas que a tela de lista mostra (nome, CPF, celular, status). Anamnese,
# odontograma, endereço etc. só são lidos ao abrir a ficha (GET /<id>).
COLUNAS_LISTA = "id, nome, cpf, telefone_whatsapp, status"
CAMPOS_ANAMNESE = {"anamnese"}


def _ocultar_prontuario(ctx, paciente):
    """Remove campos clínicos do paciente se o usuário não pode ver o prontuário."""
    if paciente and not tem_permissao(ctx, "ver_prontuario"):
        for campo in CAMPOS_PRONTUARIO:
            paciente.pop(campo, None)
    return paciente


def _exigir_permissao_edicao(ctx, campos):
    """RBAC por campo do PUT /pacientes/<id>."""
    if campos & CAMPOS_PRONTUARIO:
        exigir_permissao(ctx, "editar_prontuario")
    if campos & CAMPOS_ANAMNESE:
        exigir_alguma_permissao(ctx, "editar_pacientes", "editar_prontuario")
    if campos - CAMPOS_PRONTUARIO - CAMPOS_ANAMNESE:
        exigir_permissao(ctx, "editar_pacientes")


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


def _termos_busca(texto):
    """Normaliza o ?busca= para o filtro do banco.

    Devolve (termo_nome, termo_digitos). Remove caracteres que têm significado
    na sintaxe de filtros do PostgREST (vírgula, ponto, parênteses, aspas, curingas),
    então o texto do usuário nunca vira parte da expressão do filtro."""
    texto = re.sub(r"[^\w\s@-]", "", (texto or "").strip())[:100].strip()
    digitos = re.sub(r"\D", "", texto)
    return texto, digitos


def _filtro_busca(texto):
    """Expressão or_ (nome OU CPF OU telefone) — executada no banco."""
    nome, digitos = _termos_busca(texto)
    if not nome:
        return None
    condicoes = [f"nome.ilike.%{nome}%"]
    if digitos:
        condicoes += [f"cpf.ilike.%{digitos}%", f"telefone_whatsapp.ilike.%{digitos}%"]
    return ",".join(condicoes)


def _ultimas_consultas(clinica_id, paciente_ids):
    """Data do atendimento mais recente de cada paciente da página (só desses ids)."""
    if not paciente_ids:
        return {}
    linhas = (
        supabase.table("atendimentos")
        .select("paciente_id, data_agendada")
        .eq("clinica_id", clinica_id)
        .in_("paciente_id", paciente_ids)
        .execute()
        .data
        or []
    )
    ultima = {}
    for l in linhas:
        atual = ultima.get(l["paciente_id"])
        if l.get("data_agendada") and (atual is None or l["data_agendada"] > atual):
            ultima[l["paciente_id"]] = l["data_agendada"]
    return {pid: para_saida(v) for pid, v in ultima.items()}


@pacientes_bp.route("/", methods=["GET"])
def listar_pacientes():
    """Lista paginada: ?page=1&per_page=20 (20 a 50) e ?busca= (nome, CPF ou telefone).

    Resposta: {"items": [...], "page", "per_page", "total"}. Cada item traz
    `ultima_consulta` (antes a tela baixava TODAS as consultas para calcular isso)."""
    token = get_token(request)
    if not token:
        return jsonify({"error": "Não autorizado"}), 401

    try:
        ctx = get_contexto(token)
        exigir_permissao(ctx, "ver_pacientes")
        try:
            pag = ler_paginacao(request.args)
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        clinica_id = ctx["clinica_id"]
        if not clinica_id:
            return jsonify(envelope([], pag, 0)), 200

        filtro = _filtro_busca(request.args.get("busca"))

        def montar():
            q = supabase.table("pacientes").select(COLUNAS_LISTA, count="exact").eq("clinica_id", clinica_id)
            if filtro:
                q = q.or_(filtro)
            # id desempata pacientes criados no mesmo instante (páginas estáveis)
            return q.order("created_at", desc=True).order("id")

        itens, total = buscar_pagina(montar, pag)
        ultimas = _ultimas_consultas(clinica_id, [p["id"] for p in itens])
        for p in itens:
            _ocultar_prontuario(ctx, p)
            p["ultima_consulta"] = ultimas.get(p["id"])
        return jsonify(envelope(itens, pag, total)), 200
    except Exception as e:
        return tratar_erro(e)


@pacientes_bp.route("/opcoes", methods=["GET"])
def opcoes_pacientes():
    """Lista curta para campos de seleção (agendar consulta, lançamento, saída de estoque).

    Só id/nome/CPF/telefone. Com ?busca= devolve no máximo 20 resultados
    (autocomplete); sem busca, devolve todos os pacientes, ordenados por nome,
    com essas 4 colunas — para os <select> que listam a clínica inteira."""
    token = get_token(request)
    if not token:
        return jsonify({"error": "Não autorizado"}), 401

    try:
        ctx = get_contexto(token)
        exigir_permissao(ctx, "ver_pacientes")
        clinica_id = ctx["clinica_id"]
        if not clinica_id:
            return jsonify([]), 200
        q = (
            supabase.table("pacientes")
            .select("id, nome, cpf, telefone_whatsapp")
            .eq("clinica_id", clinica_id)
        )
        filtro = _filtro_busca(request.args.get("busca"))
        if filtro:
            q = q.or_(filtro).limit(20)
        return jsonify(q.order("nome").execute().data or []), 200
    except Exception as e:
        return tratar_erro(e)


@pacientes_bp.route("/<paciente_id>", methods=["GET"])
def obter_paciente(paciente_id):
    token = get_token(request)
    if not token:
        return jsonify({"error": "Não autorizado"}), 401

    try:
        ctx = get_contexto(token)
        exigir_permissao(ctx, "ver_pacientes")
        clinica_id = ctx["clinica_id"]
        if not clinica_id:
            return jsonify({"error": "Paciente não encontrado"}), 404
        result = supabase.table("pacientes").select("*").eq("id", paciente_id).eq("clinica_id", clinica_id).maybe_single().execute()
        if not (result and result.data):
            return jsonify({"error": "Paciente não encontrado"}), 404
        return jsonify(_ocultar_prontuario(ctx, result.data)), 200
    except Exception as e:
        return tratar_erro(e)


@pacientes_bp.route("/", methods=["POST"])
def criar_paciente():
    token = get_token(request)
    if not token:
        return jsonify({"error": "Não autorizado"}), 401

    try:
        ctx = get_contexto(token)
        exigir_permissao(ctx, "editar_pacientes")
        user_id, clinica_id = ctx["user_id"], ctx["clinica_id"]
        if not clinica_id:
            return jsonify({"error": "Perfil sem clínica vinculada. Contate o proprietário."}), 403
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify({"error": "Corpo da requisição inválido."}), 400

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

        return jsonify(_ocultar_prontuario(ctx, dict(criado))), 201
    except Exception as e:
        return tratar_erro(e)


@pacientes_bp.route("/<paciente_id>", methods=["PUT"])
def atualizar_paciente(paciente_id):
    token = get_token(request)
    if not token:
        return jsonify({"error": "Não autorizado"}), 401

    try:
        ctx = get_contexto(token)
        user_id, clinica_id = ctx["user_id"], ctx["clinica_id"]
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify({"error": "Corpo da requisição inválido."}), 400

        # Mantém apenas os campos que o cliente pode editar
        payload = {k: v for k, v in data.items() if k in CAMPOS_EDITAVEIS}

        if not payload:
            return jsonify({"error": "Nenhum campo válido para atualizar"}), 400

        # RBAC antes de qualquer leitura do banco (não confia no frontend).
        _exigir_permissao_edicao(ctx, set(payload.keys()))
        if not clinica_id:
            return jsonify({"error": "Paciente não encontrado"}), 404

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
            .maybe_single()
            .execute()
        )
        if not (atual and atual.data):
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

        return jsonify(_ocultar_prontuario(ctx, atualizado)), 200
    except Exception as e:
        return tratar_erro(e)


@pacientes_bp.route("/<paciente_id>", methods=["DELETE"])
def deletar_paciente(paciente_id):
    token = get_token(request)
    if not token:
        return jsonify({"error": "Não autorizado"}), 401

    try:
        ctx = get_contexto(token)
        # Excluir um paciente apaga o prontuário (irreversível) — só o proprietário.
        exigir_papel(ctx, "Dono")
        user_id, clinica_id = ctx["user_id"], ctx["clinica_id"]
        if not clinica_id:
            return jsonify({"error": "Paciente não encontrado"}), 404

        atual = (
            supabase.table("pacientes")
            .select("*")
            .eq("id", paciente_id)
            .eq("clinica_id", clinica_id)
            .maybe_single()
            .execute()
        )
        if not (atual and atual.data):
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
        return tratar_erro(e)

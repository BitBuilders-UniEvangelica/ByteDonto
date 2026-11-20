from collections import defaultdict
from datetime import datetime
from flask import Blueprint, request, jsonify
from app.database import supabase
from app.validators import campo_obrigatorio, validar_valor, validar_enum
from app.paginacao import buscar_pagina, envelope, ler_paginacao, quer_paginacao
from app.auth_utils import (
    get_token, get_contexto, exigir_permissao, exigir_clinica,
    pertence_a_clinica, tratar_erro,
)

financeiro_bp = Blueprint("financeiro", __name__)

STATUS_PAGAMENTO_VALIDOS = {"Pago", "Pendente", "Cancelado"}
FORMAS_PAGAMENTO_VALIDAS = {
    "Dinheiro", "Cartão Débito", "Cartão Crédito", "Pix", "Convênio",
}


@financeiro_bp.route("/", methods=["GET"])
def listar_lancamentos():
    token = get_token(request)
    if not token:
        return jsonify({"error": "Não autorizado"}), 401

    try:
        ctx = get_contexto(token)
        exigir_permissao(ctx, "ver_financeiro")
        clinica_id = ctx["clinica_id"]
        if not clinica_id:
            return jsonify([]), 200

        try:
            pag = ler_paginacao(request.args) if quer_paginacao(request.args) else None
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        # Aceita ?status= ou ?status_pagamento= (o frontend usa o segundo).
        status = request.args.get("status") or request.args.get("status_pagamento")
        paciente_id = request.args.get("paciente_id")

        def montar(count=None):
            query = (
                supabase.table("faturamento")
                .select("*, pacientes(nome), dentista:usuarios!dentista_responsavel(nome)", count=count)
                .eq("clinica_id", clinica_id)
            )
            if status:
                query = query.eq("status_pagamento", status)
            if paciente_id:
                query = query.eq("paciente_id", paciente_id)
            return query.order("created_at", desc=True).order("id")

        if pag:
            itens, total = buscar_pagina(lambda: montar("exact"), pag)
            return jsonify(envelope(itens, pag, total)), 200
        result = montar().execute()
        return jsonify(result.data), 200
    except Exception as e:
        return tratar_erro(e)


@financeiro_bp.route("/", methods=["POST"])
def criar_lancamento():
    token = get_token(request)
    if not token:
        return jsonify({"error": "Não autorizado"}), 401

    try:
        ctx = get_contexto(token)
        exigir_permissao(ctx, "ver_financeiro")
        clinica_id = exigir_clinica(ctx)
        data = request.get_json(silent=True) or {}

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

        # IDOR: todas as FKs precisam ser da mesma clínica.
        if not pertence_a_clinica("pacientes", data.get("paciente_id"), clinica_id):
            return jsonify({"error": "Paciente não encontrado nesta clínica"}), 404
        if data.get("atendimento_id") and not pertence_a_clinica("atendimentos", data.get("atendimento_id"), clinica_id):
            return jsonify({"error": "Atendimento não encontrado nesta clínica"}), 404
        if data.get("dentista_responsavel") and not pertence_a_clinica("usuarios", data.get("dentista_responsavel"), clinica_id):
            return jsonify({"error": "Dentista não encontrado nesta clínica"}), 404

        novo_lancamento = {
            "clinica_id": clinica_id,
            "paciente_id": data.get("paciente_id"),
            "atendimento_id": data.get("atendimento_id"),
            "plano_item_id": data.get("plano_item_id"),
            "dentista_responsavel": data.get("dentista_responsavel"),
            "valor": valor,
            "descricao": (data.get("descricao") or "").strip() or None,
            "forma_pagamento": forma_pagamento,
            "status_pagamento": status_pagamento,
        }

        # Remove keys com valor None para usar defaults do banco
        novo_lancamento = {k: v for k, v in novo_lancamento.items() if v is not None}

        result = supabase.table("faturamento").insert(novo_lancamento).execute()
        return jsonify(result.data[0]), 201
    except Exception as e:
        return tratar_erro(e)


@financeiro_bp.route("/<id>", methods=["PUT"])
def atualizar_lancamento(id):
    token = get_token(request)
    if not token:
        return jsonify({"error": "Não autorizado"}), 401

    try:
        ctx = get_contexto(token)
        exigir_permissao(ctx, "ver_financeiro")
        clinica_id = exigir_clinica(ctx)
        data = request.get_json(silent=True) or {}

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
            .maybe_single()
            .execute()
        )

        if not (check and check.data):
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
        return tratar_erro(e)


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
        ctx = get_contexto(token)
        exigir_permissao(ctx, "ver_financeiro")
        clinica_id = exigir_clinica(ctx)
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
        return tratar_erro(e)


@financeiro_bp.route("/resumo", methods=["GET"])
def resumo_financeiro():
    """Números dos cards e gráficos da tela Financeiro, já somados no servidor.

    Antes a tela baixava TODOS os lançamentos (com joins) para somar no navegador;
    agora a lista é paginada e os totais vêm daqui (só 4 colunas, sem joins):
      pago_mes / pendente_mes  — mês corrente (UTC, igual à tela)
      total_lancamentos        — quantidade de lançamentos da clínica
      receita_mensal           — pago nos últimos 6 meses [{mes, pago}]
      por_forma                — pago por forma de pagamento [{forma, valor}]
    """
    token = get_token(request)
    if not token:
        return jsonify({"error": "Não autorizado"}), 401

    try:
        ctx = get_contexto(token)
        exigir_permissao(ctx, "ver_financeiro")
        clinica_id = ctx["clinica_id"]
        linhas = []
        if clinica_id:
            linhas = (
                supabase.table("faturamento")
                .select("valor, status_pagamento, forma_pagamento, created_at")
                .eq("clinica_id", clinica_id)
                .execute()
                .data
                or []
            )
        return jsonify(_resumir(linhas)), 200
    except Exception as e:
        return tratar_erro(e)


def _ultimos_meses(n, hoje=None):
    hoje = hoje or datetime.utcnow()
    ano, mes = hoje.year, hoje.month
    meses = []
    for _ in range(n):
        meses.append(f"{ano:04d}-{mes:02d}")
        mes -= 1
        if mes == 0:
            ano, mes = ano - 1, 12
    return list(reversed(meses))


def _resumir(linhas, hoje=None):
    meses = _ultimos_meses(6, hoje)
    mes_atual = meses[-1]
    pago_mes = pendente_mes = 0.0
    por_mes = defaultdict(float)
    por_forma = defaultdict(float)
    for l in linhas:
        valor = float(l.get("valor") or 0)
        status = l.get("status_pagamento")
        mes = str(l.get("created_at") or "")[:7]
        if mes == mes_atual:
            if status == "Pago":
                pago_mes += valor
            elif status == "Pendente":
                pendente_mes += valor
        if status == "Pago":
            por_mes[mes] += valor
            por_forma[l.get("forma_pagamento") or "Outros"] += valor
    return {
        "mes": mes_atual,
        "pago_mes": round(pago_mes, 2),
        "pendente_mes": round(pendente_mes, 2),
        "total_lancamentos": len(linhas),
        "receita_mensal": [{"mes": m, "pago": round(por_mes[m], 2)} for m in meses],
        "por_forma": [
            {"forma": f, "valor": round(v, 2)}
            for f, v in sorted(por_forma.items(), key=lambda kv: kv[1], reverse=True)
        ],
    }


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

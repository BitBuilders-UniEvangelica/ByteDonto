"""Agenda (atendimentos).

Regras (ver também migrations/0002_agenda_e_documentos.sql, que as garante no banco):
  * Um profissional não tem dois atendimentos simultâneos na clínica.
    Intervalos semiabertos [início, início + duração): horários consecutivos
    (09:00–09:30 e 09:30–10:00) são permitidos. Cancelado não ocupa horário.
    Profissionais diferentes podem atender no mesmo horário.
  * Conflitos simultâneos: o trigger do banco serializa as gravações de agenda da
    clínica (advisory lock na transação) e confere o conflito depois do lock —
    a rota NÃO faz "consulta e depois grava" para decidir disponibilidade.
  * Fluxo de status documentado: Agendado → Aguardando → Finalizado/Cancelado/Faltou
    (Agendado também vai direto a Cancelado/Faltou/Finalizado). Finalizado,
    Cancelado e Faltou são finais e o atendimento encerrado não é remarcado.
  * Paciente e clínica do atendimento não mudam (para trocar o paciente, cancele
    e agende de novo — o histórico do prontuário fica preservado).
  * O profissional precisa ser Especialista ou Dono ativo da mesma clínica.
  * Duração entre 5 e 480 minutos (o término é sempre posterior ao início).
  * Mesmo paciente + mesmo início (não cancelado) = requisição repetida -> 409.
  * Toda criação/alteração é registrada em auditoria_prontuario.
  * Horários: ver app/horarios.py (horário de parede da clínica, sem fuso).
"""

import re
from datetime import date, datetime, timedelta, timezone

from flask import Blueprint, request, jsonify
from app.database import supabase
from app.auditoria import registrar_alteracao
from app.horarios import inicio_do_dia, normalizar_entrada, para_banco, para_saida
from app.paginacao import buscar_pagina, envelope, ler_paginacao, quer_paginacao
from app.validators import campo_obrigatorio, validar_enum
from app.auth_utils import (
    get_token, get_contexto, tem_permissao, exigir_permissao,
    exigir_alguma_permissao, exigir_clinica, pertence_a_clinica, tratar_erro,
)

consultas_bp = Blueprint("consultas", __name__)

STATUS_VALIDOS = {"Agendado", "Aguardando", "Cancelado", "Finalizado", "Faltou"}
STATUS_FINAIS = {"Finalizado", "Cancelado", "Faltou"}
# Transições permitidas (fluxo documentado + o que a agenda e o painel já fazem).
TRANSICOES = {
    "Agendado": {"Aguardando", "Faltou", "Cancelado", "Finalizado"},
    "Aguardando": {"Finalizado", "Cancelado", "Faltou"},
}
PAPEIS_PROFISSIONAIS = {"Especialista", "Dono"}

SELECT_COMPLETO = "*, pacientes(nome), dentista:usuarios!dentista_id(nome)"

# Campos do atendimento que são registro clínico (prontuário).
CAMPOS_CLINICOS = {"evolucao_clinica", "procedimentos_descritos"}
# Campos de agenda (marcação/remarcação).
CAMPOS_AGENDA = {"data_agendada", "duracao_minutos", "cadeira", "tipo_atendimento", "dentista_id"}
# Campos que definem a ocupação do horário (não mudam em atendimento encerrado).
CAMPOS_HORARIO = {"data_agendada", "duracao_minutos", "dentista_id"}
DURACAO_PADRAO = 30


def _apresentar(ctx, atendimentos):
    """Horário de parede sem fuso + evolução clínica só para quem vê o prontuário."""
    ver_prontuario = tem_permissao(ctx, "ver_prontuario")
    for a in atendimentos:
        if "data_agendada" in a:
            a["data_agendada"] = para_saida(a["data_agendada"])
        if not ver_prontuario:
            a.pop("evolucao_clinica", None)
    return atendimentos


def _ler_periodo(args):
    """?data_inicio=AAAA-MM-DD&data_fim=AAAA-MM-DD (inclusivos, horário de parede da
    clínica). Devolve (início, fim_exclusivo) para filtrar no banco, ou None."""
    inicio, fim = args.get("data_inicio"), args.get("data_fim")
    if not inicio and not fim:
        return None
    try:
        d_inicio = date.fromisoformat(inicio or fim)
        d_fim = date.fromisoformat(fim or inicio)
    except ValueError:
        raise ValueError("data_inicio/data_fim inválidas. Use o formato AAAA-MM-DD.")
    if d_fim < d_inicio:
        raise ValueError("data_fim não pode ser anterior a data_inicio.")
    if (d_fim - d_inicio).days > 366:
        raise ValueError("O período máximo da agenda é de 1 ano.")
    return inicio_do_dia(d_inicio), inicio_do_dia(d_fim + timedelta(days=1))


def _exigir_permissao_atualizacao(ctx, payload):
    """RBAC por campo do PUT /consultas/<id>."""
    campos = set(payload.keys())
    if campos & CAMPOS_CLINICOS:
        exigir_permissao(ctx, "editar_prontuario")
    if campos & CAMPOS_AGENDA:
        exigir_permissao(ctx, "agendar_consultas")
    if "queixa_principal" in campos:
        # Registrada na marcação pela recepção ou pelo dentista no atendimento.
        exigir_alguma_permissao(ctx, "agendar_consultas", "editar_prontuario")
    if "status" in campos:
        status = payload["status"]
        if status == "Cancelado":
            exigir_permissao(ctx, "cancelar_consultas")
        elif status == "Finalizado":
            # O dentista encerra o atendimento (painel do Especialista).
            exigir_alguma_permissao(ctx, "editar_prontuario", "agendar_consultas")
        else:
            # Check-in, falta — fluxo da recepção.
            exigir_permissao(ctx, "agendar_consultas")


def _validar_duracao(d):
    if d is None:
        return None
    if isinstance(d, bool) or (isinstance(d, float) and not d.is_integer()):
        raise ValueError("Duração deve ser um número inteiro de minutos.")
    try:
        n = int(d)
    except (TypeError, ValueError):
        raise ValueError("Duração deve ser um número inteiro de minutos.")
    if n < 5 or n > 480:
        raise ValueError("Duração deve estar entre 5 e 480 minutos (o término precisa ser depois do início).")
    return n


def _validar_profissional(dentista_id, clinica_id):
    """Profissional da MESMA clínica, com papel clínico e acesso ativo."""
    res = (
        supabase.table("usuarios").select("id, papel, ativo")
        .eq("id", dentista_id).eq("clinica_id", clinica_id)
        .maybe_single().execute()
    )
    perfil = res.data if res else None
    if not perfil:
        return jsonify({"error": "Profissional não encontrado nesta clínica"}), 404
    if perfil.get("papel") not in PAPEIS_PROFISSIONAIS:
        return jsonify({"error": "O responsável pelo atendimento precisa ser um profissional (Especialista ou Dono)."}), 400
    if perfil.get("ativo") is False:
        return jsonify({"error": "Este profissional está com o acesso desativado."}), 400
    return None


# ---- erros de regra vindos do banco (trigger atendimentos_validar) -----------

_ERRO_AGENDA_RE = re.compile(
    r"(CONFLITO_HORARIO|AGENDAMENTO_DUPLICADO|TRANSICAO_INVALIDA|ATENDIMENTO_ENCERRADO|"
    r"ATENDIMENTO_IMUTAVEL|DURACAO_INVALIDA)((?:\|[^|\n'\"\\}]*)*)"
)


def _resposta_erro_agenda(e):
    """Converte o RAISE do trigger em resposta HTTP. None se não for regra da agenda."""
    texto = f"{getattr(e, 'message', '') or ''} {e}"
    m = _ERRO_AGENDA_RE.search(texto)
    if not m:
        return None
    codigo, resto = m.group(1), [p.strip() for p in m.group(2).split("|")[1:]]
    if codigo == "CONFLITO_HORARIO":
        detalhe = f" ({resto[0]} às {resto[1]})" if len(resto) >= 2 else ""
        return jsonify({
            "error": f"Conflito de horário: o profissional já tem um atendimento nesse período{detalhe}. "
                     "Escolha outro horário ou outro profissional.",
            "codigo": "conflito_horario",
        }), 409
    if codigo == "AGENDAMENTO_DUPLICADO":
        return jsonify({"error": "Este paciente já tem um atendimento marcado neste mesmo horário.",
                        "codigo": "agendamento_duplicado"}), 409
    if codigo == "TRANSICAO_INVALIDA":
        de, para = (resto + ["?", "?"])[:2]
        return jsonify({"error": f"Não é possível mudar o status de '{de}' para '{para}'.",
                        "codigo": "transicao_invalida"}), 409
    if codigo == "ATENDIMENTO_ENCERRADO":
        status = resto[0] if resto else "encerrado"
        return jsonify({"error": f"Atendimento com status '{status}' não pode ser remarcado. "
                                 "Agende um novo atendimento.", "codigo": "atendimento_encerrado"}), 409
    if codigo == "ATENDIMENTO_IMUTAVEL":
        return jsonify({"error": "O paciente e a clínica de um atendimento não podem ser alterados. "
                                 "Cancele e agende um novo atendimento."}), 400
    return jsonify({"error": "Duração deve estar entre 5 e 480 minutos."}), 400


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


def _validar_transicao(atual, payload):
    """Mesmas regras do trigger, com mensagem clara antes de gravar."""
    status_atual = atual.get("status") or "Agendado"
    novo = payload.get("status", status_atual)
    if status_atual in STATUS_FINAIS:
        def _comparavel(campo, valor):
            return para_saida(valor) if campo == "data_agendada" else str(valor)

        mudou_horario = any(
            k in payload and _comparavel(k, payload[k]) != _comparavel(k, atual.get(k))
            for k in CAMPOS_HORARIO
        )
        if mudou_horario:
            return jsonify({"error": f"Atendimento com status '{status_atual}' não pode ser remarcado. "
                                     "Agende um novo atendimento.", "codigo": "atendimento_encerrado"}), 409
    if novo != status_atual and novo not in TRANSICOES.get(status_atual, set()):
        return jsonify({"error": f"Não é possível mudar o status de '{status_atual}' para '{novo}'.",
                        "codigo": "transicao_invalida"}), 409
    return None


@consultas_bp.route("/", methods=["GET"])
def listar_consultas():
    token = get_token(request)
    if not token:
        return jsonify({"error": "Não autorizado"}), 401

    try:
        ctx = get_contexto(token)
        exigir_permissao(ctx, "ver_agenda")
        clinica_id = ctx["clinica_id"]
        if not clinica_id:
            return jsonify([]), 200

        try:
            periodo = _ler_periodo(request.args)
            pag = ler_paginacao(request.args) if quer_paginacao(request.args) else None
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        paciente_id = request.args.get("paciente_id")

        def montar(count=None):
            query = (
                supabase.table("atendimentos")
                .select(SELECT_COMPLETO, count=count)
                .eq("clinica_id", clinica_id)
            )
            if paciente_id:
                query = query.eq("paciente_id", paciente_id)
            if periodo:
                # Agenda do dia/semana: o banco devolve só o período pedido.
                query = query.gte("data_agendada", periodo[0]).lt("data_agendada", periodo[1])
            return query.order("data_agendada").order("id")

        if pag:
            itens, total = buscar_pagina(lambda: montar("exact"), pag)
            return jsonify(envelope(_apresentar(ctx, itens), pag, total)), 200
        result = montar().execute()
        return jsonify(_apresentar(ctx, result.data or [])), 200
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
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify({"error": "Corpo da requisição inválido."}), 400

        try:
            campo_obrigatorio(data.get("paciente_id"), "paciente_id")
            data_agendada = para_banco(normalizar_entrada(data.get("data_agendada")))
            status = data.get("status") or "Agendado"
            validar_enum(status, STATUS_VALIDOS, "status")
            duracao = _validar_duracao(data.get("duracao_minutos"))
        except ValueError as e:
            return jsonify({"error": str(e)}), 400

        # IDOR: paciente e profissional têm que ser da mesma clínica.
        if not pertence_a_clinica("pacientes", data.get("paciente_id"), clinica_id):
            return jsonify({"error": "Paciente não encontrado nesta clínica"}), 404
        if data.get("dentista_id"):
            erro = _validar_profissional(data.get("dentista_id"), clinica_id)
            if erro:
                return erro

        novo_atendimento = {
            "clinica_id": clinica_id,
            "paciente_id": data.get("paciente_id"),
            "dentista_id": data.get("dentista_id"),
            "data_agendada": data_agendada,
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

        # Disponibilidade é decidida pelo banco (trigger + lock), dentro do INSERT.
        try:
            result = _inserir_atendimento(novo_atendimento)
        except Exception as e:
            resposta = _resposta_erro_agenda(e)
            if resposta:
                return resposta
            raise
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

        return jsonify(_apresentar(ctx, [completo.data])[0]), 201
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
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify({"error": "Corpo da requisição inválido."}), 400

        if "paciente_id" in data:
            return jsonify({"error": "O paciente de um atendimento não pode ser alterado. "
                                     "Cancele e agende um novo atendimento."}), 400

        CAMPOS_PERMITIDOS = {
            "evolucao_clinica", "status", "procedimentos_descritos", "queixa_principal",
            "tipo_atendimento", "data_agendada", "duracao_minutos", "cadeira", "dentista_id",
        }
        payload = {k: v for k, v in data.items() if k in CAMPOS_PERMITIDOS}

        if not payload:
            return jsonify({"error": "Nenhum campo válido para atualizar"}), 400

        try:
            if "status" in payload:
                validar_enum(payload["status"], STATUS_VALIDOS, "status")
            if "duracao_minutos" in payload:
                payload["duracao_minutos"] = _validar_duracao(payload["duracao_minutos"])
                if payload["duracao_minutos"] is None:
                    raise ValueError("Duração deve estar entre 5 e 480 minutos.")
            if "data_agendada" in payload:
                payload["data_agendada"] = para_banco(normalizar_entrada(payload["data_agendada"]))
            if "dentista_id" in payload and not payload["dentista_id"]:
                raise ValueError("Informe o profissional do atendimento.")
        except ValueError as e:
            return jsonify({"error": str(e)}), 400

        _exigir_permissao_atualizacao(ctx, payload)

        # Snapshot antes da alteração — auditoria e mensagens de regra
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

        if "dentista_id" in payload and payload["dentista_id"] != atual.data.get("dentista_id"):
            erro = _validar_profissional(payload["dentista_id"], clinica_id)
            if erro:
                return erro

        erro = _validar_transicao(atual.data, payload)
        if erro:
            return erro

        payload["updated_by"] = user_id
        payload["updated_at"] = datetime.now(timezone.utc).isoformat()

        # O trigger confere conflito/transição de novo, com lock, na transação.
        try:
            result = _atualizar_atendimento(payload, consulta_id, clinica_id)
        except Exception as e:
            resposta = _resposta_erro_agenda(e)
            if resposta:
                return resposta
            raise
        if not result.data:
            return jsonify({"error": "Atendimento não encontrado"}), 404

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

        return jsonify(_apresentar(ctx, [result.data[0]])[0]), 200
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

        status_atual = atual.data.get("status") or "Agendado"
        if status_atual == "Cancelado":
            # Requisição repetida: já está cancelado, nada a fazer (idempotente).
            return jsonify({"message": "Consulta cancelada"}), 200
        if status_atual in STATUS_FINAIS:
            return jsonify({"error": f"Atendimento com status '{status_atual}' não pode ser cancelado.",
                            "codigo": "transicao_invalida"}), 409

        try:
            supabase.table("atendimentos").update({
                "status": "Cancelado",
                "updated_by": user_id,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }).eq("id", consulta_id).eq("clinica_id", clinica_id).execute()
        except Exception as e:
            resposta = _resposta_erro_agenda(e)
            if resposta:
                return resposta
            raise

        registrar_alteracao(
            clinica_id=clinica_id,
            usuario_id=user_id,
            paciente_id=atual.data.get("paciente_id"),
            tabela="atendimentos",
            registro_id=consulta_id,
            acao="UPDATE",
            antes={"status": status_atual},
            depois={"status": "Cancelado"},
        )

        return jsonify({"message": "Consulta cancelada"}), 200
    except Exception as e:
        return tratar_erro(e)

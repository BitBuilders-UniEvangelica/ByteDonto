"""Esterilização — RF-020 (ciclos com parâmetros e indicadores) e RNE-011.

Fluxo: a clínica cadastra suas autoclaves (equipamentos), registra cada ciclo
com temperatura, pressão, tempo e o resultado dos indicadores químico e
biológico, e os pacotes produzidos naquele ciclo recebem código, conteúdo,
data de esterilização e data limite de uso (RDC Anvisa nº 1.002/2025).

Regras aplicadas aqui:
- O resultado do ciclo é derivado dos indicadores: qualquer indicador
  reprovado reprova o ciclo; químico aprovado + biológico aprovado (ou não
  realizado naquele ciclo) aprova; o resto fica pendente.
- RNE-011: ciclo reprovado bloqueia todos os pacotes dele, e um ciclo
  reprovado não volta a ser aprovado (o registro é a evidência sanitária).
- Pacote só fica "Disponível" com o ciclo aprovado; enquanto o ciclo está
  pendente, fica "Aguardando liberação". Pacote disponível com a data limite
  vencida é devolvido como "Vencido".
- RNE-018: não há rota de exclusão. Equipamento é inativado; ciclo e pacote
  ficam preservados.
"""

from datetime import date, datetime, timedelta, timezone
from flask import Blueprint, request, jsonify
from app.database import supabase
from app.validators import campo_obrigatorio, validar_enum
from app.auth_utils import (
    get_token, get_contexto, exigir_permissao, exigir_clinica, tratar_erro,
)

esterilizacao_bp = Blueprint("esterilizacao", __name__)

INDICADOR_QUIMICO_VALIDOS = {"Aprovado", "Reprovado", "Pendente"}
INDICADOR_BIOLOGICO_VALIDOS = {"Aprovado", "Reprovado", "Pendente", "Não realizado"}
ESTADOS_PACOTE = {"Aguardando liberação", "Disponível", "Bloqueado", "Utilizado", "Vencido"}

CAMPOS_EQUIPAMENTO = {"identificacao", "tipo", "fabricante", "modelo", "numero_serie"}


# ------------------------------------------------------------
# Regras e validações
# ------------------------------------------------------------

def resultado_do_ciclo(quimico, biologico):
    if "Reprovado" in (quimico, biologico):
        return "Reprovado"
    if quimico == "Aprovado" and biologico in ("Aprovado", "Não realizado"):
        return "Aprovado"
    return "Pendente"


def estado_inicial_do_pacote(resultado):
    return {"Aprovado": "Disponível", "Reprovado": "Bloqueado"}.get(resultado, "Aguardando liberação")


def _numero(valor, campo, minimo, maximo, inteiro=False):
    try:
        n = int(valor) if inteiro else float(valor)
    except (TypeError, ValueError):
        raise ValueError(f"O campo '{campo}' deve ser numérico.")
    if n < minimo or n > maximo:
        raise ValueError(f"O campo '{campo}' deve estar entre {minimo} e {maximo}.")
    return n


def _data_hora(valor, campo):
    campo_obrigatorio(valor, campo)
    try:
        return datetime.fromisoformat(str(valor).replace("Z", "+00:00"))
    except ValueError:
        raise ValueError(f"O campo '{campo}' deve ser uma data/hora ISO (ex.: 2026-10-27T08:30:00).")


def _validar_pacotes(pacotes, data_esterilizacao):
    """Normaliza a lista de pacotes. Cada um precisa de conteúdo e de validade
    (validade_dias ou data_limite_uso), definida pelo protocolo da clínica."""
    if not isinstance(pacotes, list):
        raise ValueError("'pacotes' deve ser uma lista.")
    limpos = []
    for idx, p in enumerate(pacotes, start=1):
        p = p or {}
        conteudo = (p.get("conteudo") or "").strip()
        if not conteudo:
            raise ValueError(f"Pacote {idx}: informe o conteúdo.")
        if p.get("data_limite_uso"):
            try:
                limite = date.fromisoformat(str(p["data_limite_uso"]))
            except ValueError:
                raise ValueError(f"Pacote {idx}: data_limite_uso inválida (use AAAA-MM-DD).")
        elif p.get("validade_dias") is not None:
            dias = _numero(p.get("validade_dias"), f"pacote {idx}: validade_dias", 1, 365, inteiro=True)
            limite = data_esterilizacao + timedelta(days=dias)
        else:
            raise ValueError(f"Pacote {idx}: informe validade_dias ou data_limite_uso.")
        if limite < data_esterilizacao:
            raise ValueError(f"Pacote {idx}: a data limite de uso não pode ser anterior à esterilização.")
        limpos.append({
            "conteudo": conteudo,
            "metodo": (p.get("metodo") or "").strip() or None,
            "data_limite_uso": limite.isoformat(),
        })
    return limpos


def _apresentar_pacote(pacote):
    """Pacote disponível com a data limite já passada sai como 'Vencido'."""
    if pacote.get("estado") == "Disponível" and str(pacote.get("data_limite_uso")) < date.today().isoformat():
        pacote = {**pacote, "estado": "Vencido"}
    return pacote


def _contexto_esterilizacao():
    ctx = get_contexto(get_token(request))
    exigir_permissao(ctx, "esterilizacao")
    return ctx, exigir_clinica(ctx)


def _buscar(tabela, registro_id, clinica_id):
    res = (
        supabase.table(tabela).select("*")
        .eq("id", registro_id).eq("clinica_id", clinica_id)
        .maybe_single().execute()
    )
    return res.data if res else None


def _inserir_pacotes(clinica_id, ciclo, equipamento, pacotes, responsavel_id):
    existentes = (
        supabase.table("pacotes_esterilizados").select("id")
        .eq("ciclo_id", ciclo["id"]).execute()
    ).data or []
    estado = estado_inicial_do_pacote(ciclo["resultado"])
    data_esterilizacao = str(ciclo["iniciado_em"])[:10]
    linhas = []
    for seq, p in enumerate(pacotes, start=len(existentes) + 1):
        linha = {
            "clinica_id": clinica_id,
            "ciclo_id": ciclo["id"],
            "codigo": f"{equipamento['identificacao']}-C{ciclo['numero_ciclo']:04d}-P{seq:02d}",
            "conteudo": p["conteudo"],
            "data_esterilizacao": data_esterilizacao,
            "data_limite_uso": p["data_limite_uso"],
            "responsavel_preparo_id": responsavel_id,
            "estado": estado,
        }
        if p.get("metodo"):
            linha["metodo"] = p["metodo"]
        linhas.append(linha)
    if not linhas:
        return []
    return supabase.table("pacotes_esterilizados").insert(linhas).execute().data


# ------------------------------------------------------------
# Equipamentos
# ------------------------------------------------------------

@esterilizacao_bp.route("/equipamentos", methods=["GET"])
def listar_equipamentos():
    try:
        _, clinica_id = _contexto_esterilizacao()
        query = supabase.table("equipamentos_esterilizacao").select("*").eq("clinica_id", clinica_id)
        if request.args.get("todos") != "1":
            query = query.eq("ativo", True)
        return jsonify(query.order("identificacao").execute().data), 200
    except Exception as e:
        return tratar_erro(e)


@esterilizacao_bp.route("/equipamentos", methods=["POST"])
def criar_equipamento():
    try:
        _, clinica_id = _contexto_esterilizacao()
        data = request.get_json(silent=True) or {}
        identificacao = (data.get("identificacao") or "").strip()
        if not identificacao:
            return jsonify({"error": "O campo 'identificacao' é obrigatório."}), 400

        repetido = (
            supabase.table("equipamentos_esterilizacao").select("id")
            .eq("clinica_id", clinica_id).eq("identificacao", identificacao).execute()
        ).data
        if repetido:
            return jsonify({"error": "Já existe um equipamento com essa identificação."}), 409

        novo = {k: (str(data[k]).strip() or None) for k in CAMPOS_EQUIPAMENTO if data.get(k) is not None}
        novo.update({"clinica_id": clinica_id, "identificacao": identificacao})
        novo = {k: v for k, v in novo.items() if v is not None}
        result = supabase.table("equipamentos_esterilizacao").insert(novo).execute()
        return jsonify(result.data[0]), 201
    except Exception as e:
        return tratar_erro(e)


@esterilizacao_bp.route("/equipamentos/<equipamento_id>", methods=["PUT"])
def atualizar_equipamento(equipamento_id):
    """Edita dados ou inativa (ativo=false). Não existe exclusão (RNE-018)."""
    try:
        _, clinica_id = _contexto_esterilizacao()
        if not _buscar("equipamentos_esterilizacao", equipamento_id, clinica_id):
            return jsonify({"error": "Equipamento não encontrado"}), 404

        data = request.get_json(silent=True) or {}
        payload = {k: data[k] for k in CAMPOS_EQUIPAMENTO if k in data}
        if "ativo" in data:
            if not isinstance(data["ativo"], bool):
                return jsonify({"error": "O campo 'ativo' deve ser true ou false."}), 400
            payload["ativo"] = data["ativo"]
        if not payload:
            return jsonify({"error": "Nenhum campo válido para atualizar"}), 400

        result = (
            supabase.table("equipamentos_esterilizacao").update(payload)
            .eq("id", equipamento_id).eq("clinica_id", clinica_id).execute()
        )
        return jsonify(result.data[0]), 200
    except Exception as e:
        return tratar_erro(e)


# ------------------------------------------------------------
# Ciclos
# ------------------------------------------------------------

@esterilizacao_bp.route("/ciclos", methods=["GET"])
def listar_ciclos():
    try:
        _, clinica_id = _contexto_esterilizacao()
        query = (
            supabase.table("ciclos_esterilizacao")
            .select("*, equipamento:equipamentos_esterilizacao!equipamento_id(identificacao), "
                    "responsavel:usuarios!responsavel_id(nome)")
            .eq("clinica_id", clinica_id)
        )
        if request.args.get("equipamento_id"):
            query = query.eq("equipamento_id", request.args["equipamento_id"])
        if request.args.get("resultado"):
            query = query.eq("resultado", request.args["resultado"])
        return jsonify(query.order("iniciado_em", desc=True).execute().data), 200
    except Exception as e:
        return tratar_erro(e)


@esterilizacao_bp.route("/ciclos", methods=["POST"])
def registrar_ciclo():
    """Registra um ciclo e, opcionalmente, os pacotes produzidos nele.

    Body: { equipamento_id, iniciado_em, temperatura_c, pressao_kgf_cm2,
            tempo_exposicao_min, indicador_quimico?, indicador_biologico?,
            observacoes?, pacotes?: [{ conteudo, metodo?, validade_dias | data_limite_uso }] }
    O número do ciclo é sequencial por equipamento e gerado pelo sistema.
    """
    try:
        ctx, clinica_id = _contexto_esterilizacao()
        data = request.get_json(silent=True) or {}

        try:
            campo_obrigatorio(data.get("equipamento_id"), "equipamento_id")
            iniciado_em = _data_hora(data.get("iniciado_em"), "iniciado_em")
            temperatura = _numero(data.get("temperatura_c"), "temperatura_c", 100, 200)
            pressao = _numero(data.get("pressao_kgf_cm2"), "pressao_kgf_cm2", 0.1, 5)
            tempo = _numero(data.get("tempo_exposicao_min"), "tempo_exposicao_min", 1, 240, inteiro=True)
            quimico = data.get("indicador_quimico") or "Pendente"
            biologico = data.get("indicador_biologico") or "Pendente"
            validar_enum(quimico, INDICADOR_QUIMICO_VALIDOS, "indicador_quimico")
            validar_enum(biologico, INDICADOR_BIOLOGICO_VALIDOS, "indicador_biologico")
            pacotes = _validar_pacotes(data.get("pacotes") or [], iniciado_em.date())
        except ValueError as e:
            return jsonify({"error": str(e)}), 400

        equipamento = _buscar("equipamentos_esterilizacao", data["equipamento_id"], clinica_id)
        if not equipamento:
            return jsonify({"error": "Equipamento não encontrado nesta clínica"}), 404
        if not equipamento.get("ativo"):
            return jsonify({"error": "Equipamento inativo não pode registrar novos ciclos."}), 400

        ultimo = (
            supabase.table("ciclos_esterilizacao").select("numero_ciclo")
            .eq("equipamento_id", equipamento["id"])
            .order("numero_ciclo", desc=True).limit(1).execute()
        ).data
        numero = (ultimo[0]["numero_ciclo"] + 1) if ultimo else 1

        novo = {
            "clinica_id": clinica_id,
            "equipamento_id": equipamento["id"],
            "numero_ciclo": numero,
            "iniciado_em": iniciado_em.isoformat(),
            "temperatura_c": temperatura,
            "pressao_kgf_cm2": pressao,
            "tempo_exposicao_min": tempo,
            "indicador_quimico": quimico,
            "indicador_biologico": biologico,
            "resultado": resultado_do_ciclo(quimico, biologico),
            "responsavel_id": ctx["user_id"],
        }
        if (data.get("observacoes") or "").strip():
            novo["observacoes"] = data["observacoes"].strip()

        ciclo = supabase.table("ciclos_esterilizacao").insert(novo).execute().data[0]
        ciclo["pacotes"] = [
            _apresentar_pacote(p)
            for p in _inserir_pacotes(clinica_id, ciclo, equipamento, pacotes, ctx["user_id"])
        ]
        return jsonify(ciclo), 201
    except Exception as e:
        return tratar_erro(e)


@esterilizacao_bp.route("/ciclos/<ciclo_id>", methods=["GET"])
def obter_ciclo(ciclo_id):
    try:
        _, clinica_id = _contexto_esterilizacao()
        ciclo = _buscar("ciclos_esterilizacao", ciclo_id, clinica_id)
        if not ciclo:
            return jsonify({"error": "Ciclo não encontrado"}), 404
        pacotes = (
            supabase.table("pacotes_esterilizados").select("*")
            .eq("ciclo_id", ciclo_id).order("codigo").execute()
        ).data or []
        ciclo["pacotes"] = [_apresentar_pacote(p) for p in pacotes]
        return jsonify(ciclo), 200
    except Exception as e:
        return tratar_erro(e)


@esterilizacao_bp.route("/ciclos/<ciclo_id>/indicadores", methods=["PUT"])
def registrar_indicadores(ciclo_id):
    """Registra a leitura dos indicadores (o biológico costuma sair depois).

    Recalcula o resultado e propaga para os pacotes:
    aprovado libera os que aguardavam; reprovado bloqueia todos (RNE-011).
    """
    try:
        _, clinica_id = _contexto_esterilizacao()
        ciclo = _buscar("ciclos_esterilizacao", ciclo_id, clinica_id)
        if not ciclo:
            return jsonify({"error": "Ciclo não encontrado"}), 404
        if ciclo["resultado"] == "Reprovado":
            return jsonify({"error": "Ciclo reprovado não pode ser alterado; registre um novo ciclo."}), 409

        data = request.get_json(silent=True) or {}
        quimico = data.get("indicador_quimico", ciclo["indicador_quimico"])
        biologico = data.get("indicador_biologico", ciclo["indicador_biologico"])
        try:
            validar_enum(quimico, INDICADOR_QUIMICO_VALIDOS, "indicador_quimico")
            validar_enum(biologico, INDICADOR_BIOLOGICO_VALIDOS, "indicador_biologico")
        except ValueError as e:
            return jsonify({"error": str(e)}), 400

        resultado = resultado_do_ciclo(quimico, biologico)
        payload = {
            "indicador_quimico": quimico,
            "indicador_biologico": biologico,
            "resultado": resultado,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        if "observacoes" in data:
            payload["observacoes"] = (data.get("observacoes") or "").strip() or None

        ciclo = (
            supabase.table("ciclos_esterilizacao").update(payload)
            .eq("id", ciclo_id).eq("clinica_id", clinica_id).execute()
        ).data[0]

        pacotes = supabase.table("pacotes_esterilizados")
        if resultado == "Reprovado":
            pacotes.update({"estado": "Bloqueado"}).eq("ciclo_id", ciclo_id) \
                .in_("estado", ["Aguardando liberação", "Disponível"]).execute()
        elif resultado == "Aprovado":
            pacotes.update({"estado": "Disponível"}).eq("ciclo_id", ciclo_id) \
                .eq("estado", "Aguardando liberação").execute()

        lista = (
            supabase.table("pacotes_esterilizados").select("*")
            .eq("ciclo_id", ciclo_id).order("codigo").execute()
        ).data or []
        ciclo["pacotes"] = [_apresentar_pacote(p) for p in lista]
        return jsonify(ciclo), 200
    except Exception as e:
        return tratar_erro(e)


@esterilizacao_bp.route("/ciclos/<ciclo_id>/pacotes", methods=["POST"])
def adicionar_pacotes(ciclo_id):
    """Acrescenta pacotes a um ciclo já registrado. Body: { pacotes: [...] }"""
    try:
        ctx, clinica_id = _contexto_esterilizacao()
        ciclo = _buscar("ciclos_esterilizacao", ciclo_id, clinica_id)
        if not ciclo:
            return jsonify({"error": "Ciclo não encontrado"}), 404
        if ciclo["resultado"] == "Reprovado":
            return jsonify({"error": "Ciclo reprovado não aceita novos pacotes."}), 409

        data = request.get_json(silent=True) or {}
        try:
            pacotes = _validar_pacotes(data.get("pacotes") or [], date.fromisoformat(str(ciclo["iniciado_em"])[:10]))
            if not pacotes:
                raise ValueError("Informe ao menos um pacote.")
        except ValueError as e:
            return jsonify({"error": str(e)}), 400

        equipamento = _buscar("equipamentos_esterilizacao", ciclo["equipamento_id"], clinica_id)
        criados = _inserir_pacotes(clinica_id, ciclo, equipamento, pacotes, ctx["user_id"])
        return jsonify([_apresentar_pacote(p) for p in criados]), 201
    except Exception as e:
        return tratar_erro(e)


# ------------------------------------------------------------
# Pacotes
# ------------------------------------------------------------

@esterilizacao_bp.route("/pacotes", methods=["GET"])
def listar_pacotes():
    """Filtros: ?ciclo_id=  ?estado=  ?disponiveis=1 (só os utilizáveis hoje)."""
    try:
        _, clinica_id = _contexto_esterilizacao()
        estado = request.args.get("estado")
        if estado and estado not in ESTADOS_PACOTE:
            return jsonify({"error": "Estado inválido."}), 400

        query = supabase.table("pacotes_esterilizados").select("*").eq("clinica_id", clinica_id)
        if request.args.get("ciclo_id"):
            query = query.eq("ciclo_id", request.args["ciclo_id"])
        if request.args.get("disponiveis") == "1":
            query = query.eq("estado", "Disponível").gte("data_limite_uso", date.today().isoformat())
        elif estado and estado != "Vencido":
            query = query.eq("estado", estado)

        pacotes = [_apresentar_pacote(p) for p in query.order("data_limite_uso").execute().data or []]
        if estado:
            pacotes = [p for p in pacotes if p["estado"] == estado]
        return jsonify(pacotes), 200
    except Exception as e:
        return tratar_erro(e)

"""Estoque — itens (materiais e insumos), lotes, fornecedores e movimentações.

Modelo:
- O saldo de um item é a soma das quantidades dos seus lotes. Controlar por
  lote permite saber a validade de cada unidade e rastrear a saída.
- Toda entrada e saída grava uma linha em movimentacoes_estoque; é o
  histórico/auditoria do estoque e nunca é apagada.
- Itens e fornecedores não são excluídos, só inativados (ativo = false),
  para não quebrar o histórico.

Status do item: "Esgotado" (saldo 0), "Estoque baixo" (saldo <= mínimo) ou "Normal".

Concorrência: entradas e saídas mexem no saldo SOMENTE pelas funções SQL
estoque_registrar_entrada / estoque_registrar_saida (migrations/0001), chamadas
via .rpc(). Cada uma roda numa transação, trava o item/lote e faz a baixa
condicional (quantidade >= pedido), então operações simultâneas não perdem
atualização, não duplicam lote e não deixam saldo negativo — nos dois modos
(local e Supabase). O CHECK (quantidade >= 0) continua como última barreira.

RBAC: todas as rotas exigem a permissão 'estoque' (PERMISSOES_PADRAO).
Isolamento: toda consulta filtra por clinica_id, e os triggers da migration
recusam referências a registros de outra clínica.
"""

from datetime import date, datetime, timedelta, timezone
from flask import Blueprint, request, jsonify
from app.database import supabase
from app.validators import validar_enum
from app.paginacao import buscar_pagina, envelope, ler_paginacao, quer_paginacao
from app.auth_utils import (
    get_token, get_contexto, exigir_permissao, exigir_clinica, tratar_erro, pertence_a_clinica,
)

estoque_bp = Blueprint("estoque", __name__)

CATEGORIAS = {"Material", "Insumo"}
UNIDADES = {"un", "cx", "pct", "par", "ml", "l", "g", "kg", "frasco", "ampola", "tubo", "seringa", "rolo"}
MOTIVOS_SAIDA = {
    "Uso em procedimento", "Vencimento", "Perda / avaria", "Ajuste de inventário", "Doação / transferência",
}
CAMPOS_FORNECEDOR = {"nome", "cnpj", "telefone", "email"}


# ------------------------------------------------------------
# Validação e helpers
# ------------------------------------------------------------

def _texto(valor):
    valor = (str(valor).strip() if valor is not None else "")
    return valor or None


def _obrigatorio(valor, rotulo):
    if _texto(valor) is None:
        raise ValueError(f"Informe {rotulo}.")
    return _texto(valor)


def _quantidade(valor, rotulo, minimo=0, permitir_zero=True):
    try:
        n = round(float(valor), 2)
    except (TypeError, ValueError):
        raise ValueError(f"{rotulo} deve ser um número.")
    if n < minimo or (not permitir_zero and n <= 0):
        raise ValueError(f"{rotulo} deve ser maior que zero." if not permitir_zero else f"{rotulo} não pode ser negativo.")
    if n > 1_000_000:
        raise ValueError(f"{rotulo} muito alto.")
    return n


def _data(valor, rotulo, obrigatoria=True, permitir_futuro=True):
    if not _texto(valor):
        if obrigatoria:
            raise ValueError(f"Informe {rotulo}.")
        return None
    try:
        d = date.fromisoformat(str(valor)[:10])
    except ValueError:
        raise ValueError(f"{rotulo.capitalize()} inválida (use AAAA-MM-DD).")
    if not permitir_futuro and d > date.today():
        raise ValueError(f"{rotulo.capitalize()} não pode ser no futuro.")
    return d


class ErroEstoque(Exception):
    """Erro de negócio com status HTTP (tratado por _tratar)."""

    def __init__(self, mensagem, status):
        super().__init__(mensagem)
        self.mensagem, self.status = mensagem, status


def _tratar(e):
    if isinstance(e, ErroEstoque):
        return jsonify({"error": e.mensagem}), e.status
    return tratar_erro(e)


def _corpo():
    """Body JSON como dict (400 para JSON inválido, lista, texto...)."""
    data = request.get_json(silent=True)
    if data is None and not request.get_data():
        return {}
    if not isinstance(data, dict):
        raise ErroEstoque("Corpo da requisição inválido.", 400)
    return data


def _mensagem_erro(e):
    """Mensagem do erro do banco: postgrest.APIError e o APIError do provider
    local expõem .message; outros erros caem no str()."""
    return getattr(e, "message", None) or str(e)


def _rpc_estoque(funcao, params):
    """Chama a função atômica e devolve (lote, movimentacao).

    Converte os RAISE EXCEPTION da função nas respostas HTTP da API."""
    try:
        linhas = supabase.rpc(funcao, params).execute().data or []
    except Exception as e:
        msg = _mensagem_erro(e)
        if "SALDO_INSUFICIENTE" in msg:
            saldo = msg.split("SALDO_INSUFICIENTE:", 1)[-1].strip().split()[0].rstrip("\"'}")
            try:
                saldo = f"{float(saldo):g}"
            except ValueError:
                pass
            raise ErroEstoque(f"Quantidade maior que o saldo do lote ({saldo}).", 409)
        if "LOTE_NAO_ENCONTRADO" in msg:
            raise ErroEstoque("Lote não encontrado para este item.", 404)
        if "ITEM_NAO_ENCONTRADO" in msg:
            raise ErroEstoque("Item não encontrado", 404)
        if "CLINICA_DIVERGENTE" in msg:
            raise ErroEstoque("Registro relacionado não pertence a esta clínica.", 400)
        raise
    if not linhas:
        raise RuntimeError(f"{funcao} não retornou dados")
    return linhas[0]["lote"], linhas[0]["movimentacao"]


def _contexto_estoque():
    ctx = get_contexto(get_token(request))
    exigir_permissao(ctx, "estoque")
    return ctx, exigir_clinica(ctx)


def _buscar(tabela, registro_id, clinica_id):
    res = (
        supabase.table(tabela).select("*")
        .eq("id", registro_id).eq("clinica_id", clinica_id)
        .maybe_single().execute()
    )
    return res.data if res else None


def status_do_item(quantidade, minimo):
    if quantidade <= 0:
        return "Esgotado"
    if quantidade <= minimo:
        return "Estoque baixo"
    return "Normal"


def _apresentar_item(item, lotes):
    """Acrescenta saldo, status e próximo vencimento a partir dos lotes com saldo."""
    com_saldo = [l for l in lotes if float(l.get("quantidade") or 0) > 0]
    quantidade = round(sum(float(l["quantidade"]) for l in com_saldo), 2)
    validades = sorted(str(l["validade"]) for l in com_saldo if l.get("validade"))
    return {
        **item,
        "quantidade_atual": quantidade,
        "status": status_do_item(quantidade, float(item.get("estoque_minimo") or 0)),
        "proximo_vencimento": validades[0] if validades else None,
    }


# Lista de itens: saldo/status/vencimento só precisam destas colunas dos lotes.
COLUNAS_LOTE_RESUMO = "item_id, quantidade, validade"
COLUNAS_ITEM_LISTA = (
    "id, nome, categoria, unidade, estoque_minimo, fornecedor_id, localizacao, observacoes, ativo, "
    "fornecedor:fornecedores_estoque!fornecedor_id(nome)"
)
COLUNAS_FORNECEDOR_LISTA = "id, nome, cnpj, telefone, email, ativo"


def _lotes_com_saldo(clinica_id, item_id=None, item_ids=None,
                     colunas="*, fornecedor:fornecedores_estoque!fornecedor_id(nome)"):
    query = (
        supabase.table("lotes_estoque")
        .select(colunas)
        .eq("clinica_id", clinica_id).gt("quantidade", 0)
    )
    if item_id:
        query = query.eq("item_id", item_id)
    if item_ids is not None:
        query = query.in_("item_id", item_ids)
    return query.order("validade").execute().data or []


def _validar_fornecedor(fornecedor_id, clinica_id):
    if fornecedor_id and not pertence_a_clinica("fornecedores_estoque", fornecedor_id, clinica_id):
        raise ValueError("Fornecedor não encontrado nesta clínica.")


def _registrar_entrada(clinica_id, item_id, quantidade, data_mov, lote, validade, fornecedor_id,
                       registrado_por, motivo="Compra / reposição", nota_fiscal=None, valor_unitario=None):
    """Soma no lote existente (mesmo código e validade) ou cria um lote novo, e grava a
    movimentação — tudo numa transação (função estoque_registrar_entrada)."""
    return _rpc_estoque("estoque_registrar_entrada", {
        "p_clinica_id": clinica_id,
        "p_item_id": item_id,
        "p_quantidade": quantidade,
        "p_data": data_mov.isoformat(),
        "p_lote": lote,
        "p_validade": validade.isoformat() if validade else None,
        "p_fornecedor_id": fornecedor_id,
        "p_registrado_por": registrado_por,
        "p_motivo": motivo,
        "p_nota_fiscal": nota_fiscal,
        "p_valor_unitario": valor_unitario,
    })


SELECT_MOVIMENTACAO = (
    "*, item:itens_estoque!item_id(nome, unidade), lote:lotes_estoque!lote_id(lote, validade), "
    "responsavel:usuarios!responsavel_id(nome), paciente:pacientes!paciente_id(nome), "
    "fornecedor:fornecedores_estoque!fornecedor_id(nome)"
)


# ------------------------------------------------------------
# Fornecedores
# ------------------------------------------------------------

@estoque_bp.route("/fornecedores", methods=["GET"])
def listar_fornecedores():
    try:
        _, clinica_id = _contexto_estoque()
        query = supabase.table("fornecedores_estoque").select(COLUNAS_FORNECEDOR_LISTA).eq("clinica_id", clinica_id)
        if request.args.get("todos") != "1":
            query = query.eq("ativo", True)
        return jsonify(query.order("nome").execute().data), 200
    except Exception as e:
        return _tratar(e)


@estoque_bp.route("/fornecedores", methods=["POST"])
def criar_fornecedor():
    try:
        _, clinica_id = _contexto_estoque()
        data = _corpo()
        nome = _texto(data.get("nome"))
        if not nome:
            return jsonify({"error": "Informe o nome do fornecedor."}), 400
        repetido = (
            supabase.table("fornecedores_estoque").select("id")
            .eq("clinica_id", clinica_id).eq("nome", nome).execute()
        ).data
        if repetido:
            return jsonify({"error": "Já existe um fornecedor com esse nome."}), 409
        novo = {k: _texto(data.get(k)) for k in CAMPOS_FORNECEDOR}
        novo = {k: v for k, v in novo.items() if v is not None}
        novo["clinica_id"] = clinica_id
        return jsonify(supabase.table("fornecedores_estoque").insert(novo).execute().data[0]), 201
    except Exception as e:
        return _tratar(e)


@estoque_bp.route("/fornecedores/<fornecedor_id>", methods=["PUT"])
def atualizar_fornecedor(fornecedor_id):
    """Edita dados ou inativa (ativo=false). Não existe exclusão."""
    try:
        _, clinica_id = _contexto_estoque()
        if not _buscar("fornecedores_estoque", fornecedor_id, clinica_id):
            return jsonify({"error": "Fornecedor não encontrado"}), 404
        data = _corpo()
        payload = {k: _texto(data[k]) for k in CAMPOS_FORNECEDOR if k in data}
        if "nome" in payload and not payload["nome"]:
            return jsonify({"error": "Informe o nome do fornecedor."}), 400
        if "ativo" in data:
            if not isinstance(data["ativo"], bool):
                return jsonify({"error": "O campo 'ativo' deve ser true ou false."}), 400
            payload["ativo"] = data["ativo"]
        if not payload:
            return jsonify({"error": "Nenhum campo válido para atualizar"}), 400
        result = (
            supabase.table("fornecedores_estoque").update(payload)
            .eq("id", fornecedor_id).eq("clinica_id", clinica_id).execute()
        )
        return jsonify(result.data[0]), 200
    except Exception as e:
        return _tratar(e)


# ------------------------------------------------------------
# Itens
# ------------------------------------------------------------

def _validar_campos_item(data, clinica_id, parcial=False):
    """Valida os campos editáveis do item. Em 'parcial', só os que vieram no body."""
    payload = {}

    def veio(campo):
        return not parcial or campo in data

    if veio("nome"):
        payload["nome"] = _obrigatorio(data.get("nome"), "o nome do item")
    if veio("categoria"):
        categoria = _obrigatorio(data.get("categoria"), "a categoria")
        validar_enum(categoria, CATEGORIAS, "categoria")
        payload["categoria"] = categoria
    if veio("unidade"):
        unidade = _obrigatorio(data.get("unidade"), "a unidade")
        validar_enum(unidade, UNIDADES, "unidade")
        payload["unidade"] = unidade
    if veio("estoque_minimo"):
        if _texto(data.get("estoque_minimo")) is None:
            raise ValueError("Informe o estoque mínimo.")
        payload["estoque_minimo"] = _quantidade(data.get("estoque_minimo"), "Estoque mínimo")
    if veio("fornecedor_id"):
        fornecedor_id = _texto(data.get("fornecedor_id"))
        _validar_fornecedor(fornecedor_id, clinica_id)
        payload["fornecedor_id"] = fornecedor_id
    for campo in ("localizacao", "observacoes"):
        if veio(campo):
            payload[campo] = _texto(data.get(campo))
    return payload


@estoque_bp.route("/itens", methods=["GET"])
def listar_itens():
    """Itens ativos com saldo, status e próximo vencimento. ?todos=1 inclui inativos."""
    try:
        _, clinica_id = _contexto_estoque()
        try:
            pag = ler_paginacao(request.args) if quer_paginacao(request.args) else None
        except ValueError as e:
            return jsonify({"error": str(e)}), 400

        def montar(count=None):
            query = (
                supabase.table("itens_estoque")
                .select(COLUNAS_ITEM_LISTA, count=count)
                .eq("clinica_id", clinica_id)
            )
            if request.args.get("todos") != "1":
                query = query.eq("ativo", True)
            return query.order("nome").order("id")

        if pag:
            itens, total = buscar_pagina(lambda: montar("exact"), pag)
            # Só os lotes dos itens desta página.
            lotes = (_lotes_com_saldo(clinica_id, item_ids=[i["id"] for i in itens], colunas=COLUNAS_LOTE_RESUMO)
                     if itens else [])
        else:
            itens, total = montar().execute().data or [], None
            lotes = _lotes_com_saldo(clinica_id, colunas=COLUNAS_LOTE_RESUMO)

        por_item = {}
        for lote in lotes:
            por_item.setdefault(lote["item_id"], []).append(lote)
        apresentados = [_apresentar_item(i, por_item.get(i["id"], [])) for i in itens]
        if pag:
            return jsonify(envelope(apresentados, pag, total)), 200
        return jsonify(apresentados), 200
    except Exception as e:
        return _tratar(e)


@estoque_bp.route("/itens", methods=["POST"])
def criar_item():
    """Body: { nome*, categoria*, unidade*, estoque_minimo*, quantidade_inicial?, lote?,
    validade?, fornecedor_id?, localizacao?, observacoes? }
    Com quantidade_inicial > 0, cria o primeiro lote e a movimentação "Estoque inicial"."""
    try:
        ctx, clinica_id = _contexto_estoque()
        data = _corpo()
        try:
            payload = _validar_campos_item(data, clinica_id)
            inicial = _quantidade(data.get("quantidade_inicial") or 0, "Quantidade inicial")
            lote = _texto(data.get("lote"))
            validade = _data(data.get("validade"), "a validade", obrigatoria=False)
        except ValueError as e:
            return jsonify({"error": str(e)}), 400

        payload = {k: v for k, v in payload.items() if v is not None}
        payload["clinica_id"] = clinica_id
        item = supabase.table("itens_estoque").insert(payload).execute().data[0]

        lotes = []
        if inicial > 0:
            lote_reg, _ = _registrar_entrada(
                clinica_id, item["id"], inicial, date.today(), lote, validade,
                payload.get("fornecedor_id"), ctx["user_id"], motivo="Estoque inicial",
            )
            lotes = [lote_reg]
        return jsonify(_apresentar_item(item, lotes)), 201
    except Exception as e:
        return _tratar(e)


@estoque_bp.route("/itens/<item_id>", methods=["GET"])
def obter_item(item_id):
    """Item com fornecedor, lotes com saldo e as últimas movimentações."""
    try:
        _, clinica_id = _contexto_estoque()
        res = (
            supabase.table("itens_estoque")
            .select("*, fornecedor:fornecedores_estoque!fornecedor_id(nome)")
            .eq("id", item_id).eq("clinica_id", clinica_id)
            .maybe_single().execute()
        )
        if not (res and res.data):
            return jsonify({"error": "Item não encontrado"}), 404
        lotes = _lotes_com_saldo(clinica_id, item_id)
        movimentacoes = (
            supabase.table("movimentacoes_estoque").select(SELECT_MOVIMENTACAO)
            .eq("clinica_id", clinica_id).eq("item_id", item_id)
            .order("data", desc=True).order("created_at", desc=True).limit(10).execute()
        ).data or []
        item = _apresentar_item(res.data, lotes)
        item["lotes"] = lotes
        item["movimentacoes"] = movimentacoes
        return jsonify(item), 200
    except Exception as e:
        return _tratar(e)


@estoque_bp.route("/itens/<item_id>", methods=["PUT"])
def atualizar_item(item_id):
    """Edita o cadastro do item. O saldo só muda por entrada/saída."""
    try:
        _, clinica_id = _contexto_estoque()
        if not _buscar("itens_estoque", item_id, clinica_id):
            return jsonify({"error": "Item não encontrado"}), 404
        data = _corpo()
        try:
            payload = _validar_campos_item(data, clinica_id, parcial=True)
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        if not payload:
            return jsonify({"error": "Nenhum campo válido para atualizar"}), 400
        payload["updated_at"] = datetime.now(timezone.utc).isoformat()
        item = (
            supabase.table("itens_estoque").update(payload)
            .eq("id", item_id).eq("clinica_id", clinica_id).execute()
        ).data[0]
        return jsonify(_apresentar_item(item, _lotes_com_saldo(clinica_id, item_id))), 200
    except Exception as e:
        return _tratar(e)


@estoque_bp.route("/itens/<item_id>", methods=["DELETE"])
def remover_item(item_id):
    """Inativa o item (some da listagem). Lotes e histórico ficam preservados."""
    try:
        _, clinica_id = _contexto_estoque()
        if not _buscar("itens_estoque", item_id, clinica_id):
            return jsonify({"error": "Item não encontrado"}), 404
        supabase.table("itens_estoque").update({
            "ativo": False, "updated_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", item_id).eq("clinica_id", clinica_id).execute()
        return jsonify({"ok": True}), 200
    except Exception as e:
        return _tratar(e)


# ------------------------------------------------------------
# Entradas e saídas
# ------------------------------------------------------------

@estoque_bp.route("/entradas", methods=["POST"])
def registrar_entrada():
    """Body: { item_id*, quantidade*, lote*, validade*, fornecedor_id*, data*,
    nota_fiscal?, valor_unitario? }"""
    try:
        ctx, clinica_id = _contexto_estoque()
        data = _corpo()
        try:
            item_id = _obrigatorio(data.get("item_id"), "o item")
            quantidade = _quantidade(data.get("quantidade"), "Quantidade", permitir_zero=False)
            lote = _obrigatorio(data.get("lote"), "o lote")
            validade = _data(data.get("validade"), "a validade")
            fornecedor_id = _obrigatorio(data.get("fornecedor_id"), "o fornecedor")
            _validar_fornecedor(fornecedor_id, clinica_id)
            data_entrada = _data(data.get("data"), "a data da entrada", permitir_futuro=False)
            valor = data.get("valor_unitario")
            valor_unitario = _quantidade(valor, "Valor unitário") if _texto(valor) is not None else None
        except ValueError as e:
            return jsonify({"error": str(e)}), 400

        item = _buscar("itens_estoque", item_id, clinica_id)
        if not item:
            return jsonify({"error": "Item não encontrado"}), 404
        if not item.get("ativo"):
            return jsonify({"error": "Item inativo não recebe entradas."}), 400

        lote_reg, movimentacao = _registrar_entrada(
            clinica_id, item_id, quantidade, data_entrada, lote, validade, fornecedor_id,
            ctx["user_id"], nota_fiscal=_texto(data.get("nota_fiscal")), valor_unitario=valor_unitario,
        )
        return jsonify({"lote": lote_reg, "movimentacao": movimentacao}), 201
    except Exception as e:
        return _tratar(e)


@estoque_bp.route("/saidas", methods=["POST"])
def registrar_saida():
    """Body: { item_id*, lote_id*, quantidade*, motivo*, data*, responsavel_id*,
    paciente_id?, procedimento?, observacao? }. Não deixa sair mais que o saldo do lote."""
    try:
        ctx, clinica_id = _contexto_estoque()
        data = _corpo()
        try:
            item_id = _obrigatorio(data.get("item_id"), "o item")
            lote_id = _obrigatorio(data.get("lote_id"), "o lote")
            quantidade = _quantidade(data.get("quantidade"), "Quantidade", permitir_zero=False)
            motivo = _obrigatorio(data.get("motivo"), "o motivo")
            validar_enum(motivo, MOTIVOS_SAIDA, "motivo")
            data_saida = _data(data.get("data"), "a data da saída", permitir_futuro=False)
            responsavel_id = _obrigatorio(data.get("responsavel_id"), "o responsável")
            paciente_id = _texto(data.get("paciente_id"))
            if not pertence_a_clinica("usuarios", responsavel_id, clinica_id):
                raise ValueError("Responsável não encontrado nesta clínica.")
            if paciente_id and not pertence_a_clinica("pacientes", paciente_id, clinica_id):
                raise ValueError("Paciente não encontrado nesta clínica.")
        except ValueError as e:
            return jsonify({"error": str(e)}), 400

        # Validação do lote e baixa do saldo são atômicas (estoque_registrar_saida):
        # nada de "ler o saldo e depois gravar" aqui.
        lote, movimentacao = _rpc_estoque("estoque_registrar_saida", {
            "p_clinica_id": clinica_id,
            "p_item_id": item_id,
            "p_lote_id": lote_id,
            "p_quantidade": quantidade,
            "p_data": data_saida.isoformat(),
            "p_motivo": motivo,
            "p_responsavel_id": responsavel_id,
            "p_registrado_por": ctx["user_id"],
            "p_paciente_id": paciente_id,
            "p_procedimento": _texto(data.get("procedimento")),
            "p_observacao": _texto(data.get("observacao")),
        })
        return jsonify({"lote": lote, "movimentacao": movimentacao}), 201
    except Exception as e:
        return _tratar(e)


# ------------------------------------------------------------
# Histórico e resumo
# ------------------------------------------------------------

@estoque_bp.route("/movimentacoes", methods=["GET"])
def listar_movimentacoes():
    """Filtros: ?item_id=  ?tipo=Entrada|Saída  ?limit= (padrão 200, máx. 1000).
    Com ?page=&per_page= devolve {items, page, per_page, total} (20 a 50 por página)."""
    try:
        _, clinica_id = _contexto_estoque()
        tipo = request.args.get("tipo")
        if tipo and tipo not in ("Entrada", "Saída"):
            return jsonify({"error": "Tipo inválido."}), 400
        try:
            pag = ler_paginacao(request.args) if quer_paginacao(request.args) else None
        except ValueError as e:
            return jsonify({"error": str(e)}), 400

        def montar(count=None):
            q = supabase.table("movimentacoes_estoque").select(SELECT_MOVIMENTACAO, count=count).eq("clinica_id", clinica_id)
            if request.args.get("item_id"):
                q = q.eq("item_id", request.args["item_id"])
            if tipo:
                q = q.eq("tipo", tipo)
            return q

        if pag:
            itens, total = buscar_pagina(
                lambda: montar("exact").order("data", desc=True).order("created_at", desc=True).order("id"), pag)
            return jsonify(envelope(itens, pag, total)), 200
        query = montar()
        try:
            limite = max(1, min(int(request.args.get("limit", 200)), 1000))
        except ValueError:
            limite = 200
        dados = query.order("data", desc=True).order("created_at", desc=True).limit(limite).execute().data
        return jsonify(dados or []), 200
    except Exception as e:
        return _tratar(e)


@estoque_bp.route("/resumo", methods=["GET"])
def resumo():
    """Movimentações no mês e os itens mais consumidos (saídas) nos últimos ?dias= (padrão 30)."""
    try:
        _, clinica_id = _contexto_estoque()
        try:
            dias = max(1, min(int(request.args.get("dias", 30)), 365))
        except ValueError:
            dias = 30
        hoje = date.today()
        desde = min(hoje.replace(day=1), hoje - timedelta(days=dias))
        movs = (
            supabase.table("movimentacoes_estoque")
            .select("item_id, tipo, quantidade, data, item:itens_estoque!item_id(nome, unidade)")
            .eq("clinica_id", clinica_id).gte("data", desde.isoformat()).execute()
        ).data or []

        inicio_mes = hoje.replace(day=1).isoformat()
        inicio_periodo = (hoje - timedelta(days=dias)).isoformat()
        consumo = {}
        for m in movs:
            if m["tipo"] == "Saída" and str(m["data"]) >= inicio_periodo:
                atual = consumo.setdefault(m["item_id"], {
                    "item_id": m["item_id"],
                    "nome": (m.get("item") or {}).get("nome"),
                    "unidade": (m.get("item") or {}).get("unidade"),
                    "quantidade": 0,
                })
                atual["quantidade"] = round(atual["quantidade"] + float(m["quantidade"]), 2)
        mais = sorted(consumo.values(), key=lambda c: c["quantidade"], reverse=True)[:5]
        return jsonify({
            "dias": dias,
            "movimentacoes_mes": sum(1 for m in movs if str(m["data"]) >= inicio_mes),
            "mais_consumidos": mais,
        }), 200
    except Exception as e:
        return _tratar(e)

from flask import Blueprint, request, jsonify
from app.database import supabase
from app.validators import campo_obrigatorio

planos_bp = Blueprint("planos", __name__)


def get_token(req):
    return req.headers.get("Authorization", "").replace("Bearer ", "")


def get_user_clinica(token):
    user = supabase.auth.get_user(token).user
    perfil = supabase.table("usuarios").select("clinica_id").eq("id", user.id).single().execute()
    return user.id, perfil.data["clinica_id"]


@planos_bp.route("/", methods=["GET"])
def listar_planos():
    token = get_token(request)
    if not token:
        return jsonify({"error": "Nao autorizado"}), 401

    paciente_id = request.args.get("paciente_id")
    if not paciente_id:
        return jsonify({"error": "paciente_id e obrigatorio"}), 400

    try:
        _, clinica_id = get_user_clinica(token)

        planos = (
            supabase.table("planos_tratamento")
            .select("*, dentista:usuarios(nome)")
            .eq("clinica_id", clinica_id)
            .eq("paciente_id", paciente_id)
            .execute()
        )

        for plano in planos.data:
            itens = (
                supabase.table("plano_itens")
                .select("*")
                .eq("plano_id", plano["id"])
                .order("ordem")
                .execute()
            )
            plano["itens"] = itens.data

        return jsonify(planos.data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@planos_bp.route("/", methods=["POST"])
def criar_plano():
    token = get_token(request)
    if not token:
        return jsonify({"error": "Nao autorizado"}), 401

    try:
        user_id, clinica_id = get_user_clinica(token)
        data = request.get_json() or {}

        itens_payload = data.get("itens", [])

        try:
            campo_obrigatorio(data.get("paciente_id"), "paciente_id")
            for idx, item in enumerate(itens_payload):
                quantidade = item.get("quantidade", 1) or 1
                valor_unitario = item.get("valor_unitario", 0) or 0
                try:
                    quantidade = float(quantidade)
                    valor_unitario = float(valor_unitario)
                except (TypeError, ValueError):
                    raise ValueError(f"Item {idx + 1}: quantidade e valor unitário devem ser numéricos.")
                if quantidade <= 0:
                    raise ValueError(f"Item {idx + 1}: a quantidade deve ser maior que zero.")
                if valor_unitario < 0:
                    raise ValueError(f"Item {idx + 1}: o valor unitário não pode ser negativo.")
        except ValueError as e:
            return jsonify({"error": str(e)}), 400

        paciente_id = data.get("paciente_id")

        valor_total = sum(
            (item.get("quantidade", 1) or 1) * (item.get("valor_unitario", 0) or 0)
            for item in itens_payload
        )

        novo_plano = {
            "clinica_id": clinica_id,
            "paciente_id": paciente_id,
            "dentista_id": user_id,
            "titulo": data.get("titulo", "Plano de Tratamento"),
            "observacoes": data.get("observacoes"),
            "valor_total": valor_total,
        }
        novo_plano = {k: v for k, v in novo_plano.items() if v is not None}

        plano_result = supabase.table("planos_tratamento").insert(novo_plano).execute()
        plano = plano_result.data[0]
        plano_id = plano["id"]

        itens_inseridos = []
        for idx, item in enumerate(itens_payload):
            novo_item = {
                "plano_id": plano_id,
                "procedimento": item.get("procedimento"),
                "dente": item.get("dente"),
                "quantidade": item.get("quantidade", 1),
                "valor_unitario": item.get("valor_unitario", 0),
                "ordem": idx,
            }
            novo_item = {k: v for k, v in novo_item.items() if v is not None}
            item_result = supabase.table("plano_itens").insert(novo_item).execute()
            itens_inseridos.append(item_result.data[0])

        plano["itens"] = itens_inseridos
        return jsonify(plano), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@planos_bp.route("/<plano_id>", methods=["PUT"])
def atualizar_plano(plano_id):
    token = get_token(request)
    if not token:
        return jsonify({"error": "Nao autorizado"}), 401

    try:
        _, clinica_id = get_user_clinica(token)
        data = request.get_json()

        CAMPOS_PERMITIDOS = {"status", "observacoes", "titulo"}
        payload = {k: v for k, v in data.items() if k in CAMPOS_PERMITIDOS}

        if not payload:
            return jsonify({"error": "Nenhum campo valido para atualizar"}), 400

        check = (
            supabase.table("planos_tratamento")
            .select("id")
            .eq("id", plano_id)
            .eq("clinica_id", clinica_id)
            .single()
            .execute()
        )

        if not check.data:
            return jsonify({"error": "Plano nao encontrado"}), 404

        result = (
            supabase.table("planos_tratamento")
            .update(payload)
            .eq("id", plano_id)
            .eq("clinica_id", clinica_id)
            .execute()
        )
        return jsonify(result.data[0]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@planos_bp.route("/<plano_id>/itens/<item_id>", methods=["PUT"])
def atualizar_item(plano_id, item_id):
    token = get_token(request)
    if not token:
        return jsonify({"error": "Nao autorizado"}), 401

    try:
        _, clinica_id = get_user_clinica(token)
        data = request.get_json()

        CAMPOS_PERMITIDOS = {"status"}
        payload = {k: v for k, v in data.items() if k in CAMPOS_PERMITIDOS}

        if not payload:
            return jsonify({"error": "Nenhum campo valido para atualizar"}), 400

        # Confirm the plano belongs to the clinic before touching its items
        plano = (
            supabase.table("planos_tratamento")
            .select("id, paciente_id, dentista_id")
            .eq("id", plano_id)
            .eq("clinica_id", clinica_id)
            .single()
            .execute()
        )

        if not plano.data:
            return jsonify({"error": "Plano nao encontrado"}), 404

        # Snapshot do item antes da mudança — saber se houve transição de status
        atual = (
            supabase.table("plano_itens")
            .select("*")
            .eq("id", item_id)
            .eq("plano_id", plano_id)
            .single()
            .execute()
        )
        if not atual.data:
            return jsonify({"error": "Item nao encontrado"}), 404

        result = (
            supabase.table("plano_itens")
            .update(payload)
            .eq("id", item_id)
            .eq("plano_id", plano_id)
            .execute()
        )

        novo_status = payload.get("status")
        status_anterior = atual.data.get("status")

        # Ao concluir um item, dispara o lançamento financeiro pendente
        # vinculado a esse item — assim a recepção não esquece de cobrar.
        if novo_status == "Concluido" and status_anterior != "Concluido":
            _gerar_faturamento_do_item(clinica_id, plano.data, atual.data)
        # Se voltou pra pendente, cancela qualquer lançamento aberto desse item
        elif novo_status == "Pendente" and status_anterior == "Concluido":
            _cancelar_faturamento_do_item(clinica_id, item_id)

        return jsonify(result.data[0]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def _gerar_faturamento_do_item(clinica_id, plano, item):
    """Cria lançamento Pendente quando um item do plano é concluído.

    É idempotente: se já existe lançamento ativo (não-cancelado) pra esse item,
    não cria outro. Falhas aqui não derrubam a conclusão do item.
    """
    try:
        item_id = item["id"]
        existente = (
            supabase.table("faturamento")
            .select("id, status_pagamento")
            .eq("plano_item_id", item_id)
            .eq("clinica_id", clinica_id)
            .neq("status_pagamento", "Cancelado")
            .execute()
        )
        if existente.data:
            return

        valor = float(item.get("valor_unitario") or 0) * (int(item.get("quantidade") or 1))
        if valor <= 0:
            return

        proc = item.get("procedimento") or "Procedimento"
        if item.get("dente"):
            descricao = f"{proc} (dente {item['dente']})"
        else:
            descricao = proc

        supabase.table("faturamento").insert({
            "clinica_id": clinica_id,
            "paciente_id": plano.get("paciente_id"),
            "plano_item_id": item_id,
            "dentista_responsavel": plano.get("dentista_id"),
            "valor": valor,
            "descricao": descricao,
            "status_pagamento": "Pendente",
        }).execute()
    except Exception:
        pass


def _cancelar_faturamento_do_item(clinica_id, item_id):
    """Cancela lançamentos pendentes ligados a um item que voltou pra Pendente."""
    try:
        supabase.table("faturamento").update({
            "status_pagamento": "Cancelado",
        }).eq("plano_item_id", item_id).eq("clinica_id", clinica_id).eq("status_pagamento", "Pendente").execute()
    except Exception:
        pass


@planos_bp.route("/<plano_id>", methods=["DELETE"])
def deletar_plano(plano_id):
    token = get_token(request)
    if not token:
        return jsonify({"error": "Nao autorizado"}), 401

    try:
        _, clinica_id = get_user_clinica(token)

        check = (
            supabase.table("planos_tratamento")
            .select("id")
            .eq("id", plano_id)
            .eq("clinica_id", clinica_id)
            .single()
            .execute()
        )

        if not check.data:
            return jsonify({"error": "Plano nao encontrado"}), 404

        supabase.table("planos_tratamento").delete().eq("id", plano_id).eq("clinica_id", clinica_id).execute()
        return jsonify({"message": "Plano deletado com sucesso"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

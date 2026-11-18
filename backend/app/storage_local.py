"""Entrega dos arquivos do storage local (DATA_BACKEND=local).

Substitui as signed URLs do Supabase Storage. Só é registrado no modo local.

O link é gerado por app.database._Bucket.create_signed_url e só funciona com
um token válido (assinado com JWT_SECRET, com validade e preso ao arquivo).
"""

import os

import jwt
from flask import Blueprint, abort, request, send_from_directory

from config import Config

storage_bp = Blueprint("storage_local", __name__)


@storage_bp.route("/<bucket>/<path:caminho>", methods=["GET"])
def servir_arquivo(bucket, caminho):
    token = request.args.get("token", "")
    try:
        dados = jwt.decode(token, Config.JWT_SECRET, algorithms=["HS256"])
    except jwt.PyJWTError:
        abort(403)
    if dados.get("bucket") != bucket or dados.get("path") != caminho:
        abort(403)
    # send_from_directory já bloqueia "../" (path traversal)
    resposta = send_from_directory(os.path.join(Config.STORAGE_DIR, bucket), caminho)
    # Arquivos de paciente: o navegador não pode "adivinhar" outro tipo.
    resposta.headers["X-Content-Type-Options"] = "nosniff"
    resposta.headers["Cache-Control"] = "private, no-store"
    return resposta

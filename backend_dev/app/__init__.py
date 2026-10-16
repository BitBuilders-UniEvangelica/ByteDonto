import os
from flask import Flask, jsonify
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix
from config import Config
from app.extensions import limiter

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Railway (e qualquer proxy reverso) entrega o IP real do cliente no
    # X-Forwarded-For. Sem isso, request.remote_addr seria sempre o IP do
    # proxy e o rate limiting por IP não funcionaria (todo mundo cairia no
    # mesmo balde).
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    allowed_origins = [
        origem.strip()
        for origem in os.getenv(
            "ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000"
        ).split(",")
        if origem.strip()
    ]
    CORS(app, resources={r"/api/*": {"origins": allowed_origins}})

    # Rate limiting global — mitiga força bruta e abuso da API. Limite padrão
    # generoso (não afeta uso normal); rotas sensíveis (login, registro) têm
    # limites mais estritos definidos localmente. Em produção sem REDIS_URL,
    # usa armazenamento em memória do próprio processo (suficiente para o
    # único worker do gunicorn configurado no Procfile/railway.json).
    app.config["RATELIMIT_STORAGE_URI"] = os.getenv("RATELIMIT_STORAGE_URI", "memory://")
    app.config["RATELIMIT_HEADERS_ENABLED"] = True
    app.config["RATELIMIT_DEFAULT"] = "300 per minute;3000 per hour"
    limiter.init_app(app)

    @app.errorhandler(429)
    def limite_excedido(e):
        return jsonify({
            "error": "Muitas requisições. Aguarde um instante e tente novamente."
        }), 429

    # Registrar blueprints
    from app.auth.routes import auth_bp
    from app.pacientes.routes import pacientes_bp
    from app.consultas.routes import consultas_bp
    from app.clinicas.routes import clinicas_bp
    from app.usuarios.routes import usuarios_bp
    from app.financeiro.routes import financeiro_bp
    from app.dashboard.routes import dashboard_bp
    from app.planos.routes import planos_bp
    from app.imagens.routes import imagens_bp
    from app.storage_local import storage_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(pacientes_bp, url_prefix="/api/pacientes")
    app.register_blueprint(consultas_bp, url_prefix="/api/consultas")
    app.register_blueprint(clinicas_bp, url_prefix="/api/clinicas")
    app.register_blueprint(usuarios_bp, url_prefix="/api/usuarios")
    app.register_blueprint(financeiro_bp, url_prefix="/api/financeiro")
    app.register_blueprint(dashboard_bp, url_prefix="/api/dashboard")
    app.register_blueprint(planos_bp, url_prefix="/api/planos")
    app.register_blueprint(imagens_bp, url_prefix="/api/imagens")
    # Só no backend_dev: entrega os arquivos do storage local (links assinados)
    app.register_blueprint(storage_bp, url_prefix="/api/storage")

    @app.route("/api/health")
    @limiter.exempt
    def health():
        return {"status": "ok", "message": "ByteDonto API rodando", "ambiente": "dev (PostgreSQL local)"}

    return app

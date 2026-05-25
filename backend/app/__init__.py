import os
from flask import Flask
from flask_cors import CORS
from config import Config

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    allowed_origins = [
        origem.strip()
        for origem in os.getenv(
            "ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000"
        ).split(",")
        if origem.strip()
    ]
    CORS(app, resources={r"/api/*": {"origins": allowed_origins}})

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

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(pacientes_bp, url_prefix="/api/pacientes")
    app.register_blueprint(consultas_bp, url_prefix="/api/consultas")
    app.register_blueprint(clinicas_bp, url_prefix="/api/clinicas")
    app.register_blueprint(usuarios_bp, url_prefix="/api/usuarios")
    app.register_blueprint(financeiro_bp, url_prefix="/api/financeiro")
    app.register_blueprint(dashboard_bp, url_prefix="/api/dashboard")
    app.register_blueprint(planos_bp, url_prefix="/api/planos")
    app.register_blueprint(imagens_bp, url_prefix="/api/imagens")

    @app.route("/api/health")
    def health():
        return {"status": "ok", "message": "ByteDonto API rodando"}

    return app

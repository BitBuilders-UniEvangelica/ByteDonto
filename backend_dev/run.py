import os
from app import create_app

app = create_app()

if __name__ == "__main__":
    debug = os.getenv("FLASK_DEBUG", "True").lower() == "true"
    # Porta 8001 para poder rodar ao lado do backend de produção (8000)
    app.run(debug=debug, port=int(os.getenv("PORT", "8001")))

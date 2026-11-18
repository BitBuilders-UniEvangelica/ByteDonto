import os
from app import create_app

app = create_app()

if __name__ == "__main__":
    debug = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    # PORT permite rodar o modo local na 8001 (porta que o proxy do Vite usa por padrão).
    app.run(debug=debug, port=int(os.getenv("PORT", "8000")))

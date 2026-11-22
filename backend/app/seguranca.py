"""Cabeçalhos de segurança HTTP em todas as respostas da API.

Feito à mão (em vez do flask-talisman) para não forçar redirecionamento a
HTTPS: quem termina o TLS é o provedor de hospedagem, e no ambiente local a
API roda em HTTP. O HSTS só é enviado quando a requisição chegou por HTTPS.
"""

from flask import request

# A API só devolve JSON: nada nela precisa carregar script, estilo ou ser
# exibido dentro de outra página.
CSP_API = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"

# Rotas que entregam arquivos (imagens e PDFs do storage local). Ficam sem a
# CSP acima para o navegador conseguir abrir o PDF no visualizador próprio.
PREFIXOS_ARQUIVO = ("/api/storage/",)


def registrar_cabecalhos(app):
    @app.after_request
    def cabecalhos_de_seguranca(resposta):
        h = resposta.headers
        h.setdefault("X-Content-Type-Options", "nosniff")
        h.setdefault("X-Frame-Options", "DENY")
        # Os links assinados levam o token na URL: não vazam por Referer.
        h.setdefault("Referrer-Policy", "no-referrer")
        h.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        h.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        if not request.path.startswith(PREFIXOS_ARQUIVO):
            h.setdefault("Content-Security-Policy", CSP_API)
            # Dados de saúde: navegador e proxies não guardam cópia.
            h.setdefault("Cache-Control", "no-store")
        if request.is_secure:
            h.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return resposta

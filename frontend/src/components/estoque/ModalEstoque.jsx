import { AlertTriangle } from "lucide-react";

/* Base dos modais do estoque. Segue o padrão do sistema: sem "X" no topo;
   fecha pelo botão Cancelar do rodapé, ao lado da ação principal. */
export default function ModalEstoque({
    titulo, subtitulo, erro, onCancelar, onSalvar, textoSalvar = "Salvar", salvando = false,
    largura = 640, children,
}) {
    function enviar(e) {
        e.preventDefault();
        if (!salvando) onSalvar();
    }

    return (
        <div className="modal-overlay" style={{ zIndex: 9999 }}>
            <div className="modal-caixa est-modal" role="dialog" aria-modal="true" aria-label={titulo} style={{ maxWidth: `${largura}px` }}>
                <h2 className="est-modal-titulo">{titulo}</h2>
                {subtitulo && <p className="est-modal-sub">{subtitulo}</p>}

                <form onSubmit={enviar} noValidate>
                    {erro && (
                        <div className="est-modal-erro">
                            <AlertTriangle size={16} strokeWidth={2} /> {erro}
                        </div>
                    )}
                    {children}
                    <div className="est-modal-rodape">
                        <button type="button" className="est-btn" onClick={onCancelar} disabled={salvando}>Cancelar</button>
                        <button type="submit" className="est-btn primario" disabled={salvando}>
                            {salvando ? "Salvando..." : textoSalvar}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}

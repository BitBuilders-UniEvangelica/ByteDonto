import { ChevronLeft, ChevronRight } from "lucide-react";
import "../../styles/Paginacao.css";

/* Controles de paginação das listas (anterior / próxima + total).
   Recebe o envelope do backend: { page, per_page, total }. */
function Paginacao({ page, perPage, total, onMudarPagina, carregando = false, rotulo = "registros" }) {
    if (!total) return null;
    const totalPaginas = Math.max(1, Math.ceil(total / perPage));
    const primeiro = (page - 1) * perPage + 1;
    const ultimo = Math.min(page * perPage, total);

    return (
        <nav className="paginacao" aria-label="Paginação">
            <p className="paginacao-info">
                {primeiro > total
                    ? `${total} ${rotulo}`
                    : `${primeiro}–${ultimo} de ${total} ${rotulo}`}
            </p>
            <div className="paginacao-acoes">
                <button
                    type="button"
                    className="paginacao-btn"
                    onClick={() => onMudarPagina(page - 1)}
                    disabled={carregando || page <= 1}
                    aria-label="Página anterior"
                >
                    <ChevronLeft size={16} /> Anterior
                </button>
                <span className="paginacao-pagina">Página {page} de {totalPaginas}</span>
                <button
                    type="button"
                    className="paginacao-btn"
                    onClick={() => onMudarPagina(page + 1)}
                    disabled={carregando || page >= totalPaginas}
                    aria-label="Próxima página"
                >
                    Próxima <ChevronRight size={16} />
                </button>
            </div>
        </nav>
    );
}

export default Paginacao;

import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { useAuth } from "../../../context/AuthContext";
import { useRotas } from "../../../hooks/useRotas";
import { apiGetItensEstoque, apiGetMovimentacoesEstoque } from "../../../services/api";
import { Banner } from "../../../components/feedback/Feedback";
import PaginaEstoque from "../../../components/estoque/PaginaEstoque";
import TabelaMovimentacoes from "../../../components/estoque/TabelaMovimentacoes";

const TIPOS = [
    { id: "", rotulo: "Todas" },
    { id: "Entrada", rotulo: "Entradas" },
    { id: "Saída", rotulo: "Saídas" },
];
const LIMITE = 500;

/* Histórico completo de entradas e saídas, filtrável por item e tipo.
   O item vem da URL (?item=<id>) quando a tela é aberta pelos detalhes do item. */
export default function HistoricoEstoque() {
    const { token } = useAuth();
    const [params, setParams] = useSearchParams();
    const { rota } = useRotas();
    const itemId = params.get("item") || "";
    const tipo = params.get("tipo") || "";

    const [itens, setItens] = useState([]);
    const [movs, setMovs] = useState(null);
    const [erro, setErro] = useState(false);

    useEffect(() => {
        if (!token) return;
        // ?todos=1 não existe no front: itens removidos aparecem pelo nome na tabela
        apiGetItensEstoque(token).then(d => setItens(Array.isArray(d) ? d : [])).catch(() => {});
    }, [token]);

    function carregar() {
        if (!token) return;
        apiGetMovimentacoesEstoque(token, { itemId, tipo, limit: LIMITE })
            .then(d => { setMovs(Array.isArray(d) ? d : []); setErro(false); })
            .catch(() => { setMovs([]); setErro(true); });
    }
     
    useEffect(carregar, [token, itemId, tipo]);

    function filtrar(chave, valor) {
        const novos = new URLSearchParams(params);
        if (valor) novos.set(chave, valor); else novos.delete(chave);
        setMovs(null);
        setParams(novos, { replace: true });
    }

    return (
        <PaginaEstoque>
            <div>
                <Link className="est-voltar" to={rota(itemId ? `estoque/item/${itemId}` : "estoque")}>
                    <ArrowLeft size={16} strokeWidth={2} /> {itemId ? "Voltar para o item" : "Voltar para Estoque"}
                </Link>
                <div className="est-header">
                    <div>
                        <h1>Histórico do Estoque</h1>
                        <p>Todas as entradas e saídas registradas.</p>
                    </div>
                </div>
            </div>

            {erro && <Banner texto="Não foi possível carregar o histórico." onTentarNovamente={carregar} />}

            <div className="est-card">
                <div className="est-filtros">
                    <select className="est-busca" value={itemId} onChange={e => filtrar("item", e.target.value)} aria-label="Filtrar por item">
                        <option value="">Todos os itens</option>
                        {itens.map(i => <option key={i.id} value={i.id}>{i.nome}</option>)}
                    </select>
                    <div className="est-abas" role="tablist">
                        {TIPOS.map(t => (
                            <button
                                key={t.id || "todas"}
                                type="button"
                                role="tab"
                                aria-selected={tipo === t.id}
                                className={`est-aba ${tipo === t.id ? "ativa" : ""}`}
                                onClick={() => filtrar("tipo", t.id)}
                            >
                                {t.rotulo}
                            </button>
                        ))}
                    </div>
                </div>

                {movs === null ? (
                    <p className="est-vazio" style={{ padding: "4rem 1rem" }}>Carregando...</p>
                ) : (
                    <>
                        <TabelaMovimentacoes movimentacoes={movs} mostrarItem={!itemId} vazio="Nenhuma movimentação encontrada." />
                        {movs.length >= LIMITE && (
                            <p className="est-vazio" style={{ padding: "1rem 0 0" }}>Mostrando as {LIMITE} movimentações mais recentes.</p>
                        )}
                    </>
                )}
            </div>
        </PaginaEstoque>
    );
}

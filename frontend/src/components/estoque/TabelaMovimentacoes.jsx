import { formatDate } from "../../utils/formatters";
import { descreverMotivo, qtdComSinal } from "./estoqueUtils";

/* Tabela de movimentações (usada nos detalhes do item e no histórico).
   mostrarItem: inclui a coluna "Item" (no histórico geral). */
export default function TabelaMovimentacoes({ movimentacoes, unidade, mostrarItem = false, vazio = "Nenhuma movimentação registrada." }) {
    if (!movimentacoes.length) return <p className="est-vazio">{vazio}</p>;
    return (
        <div className="est-tabela-wrap">
            <table className="est-tabela">
                <thead>
                    <tr>
                        <th>Data</th>
                        {mostrarItem && <th>Item</th>}
                        <th>Tipo</th>
                        <th>Quantidade</th>
                        <th>Lote</th>
                        <th>Motivo</th>
                        <th>Responsável</th>
                    </tr>
                </thead>
                <tbody>
                    {movimentacoes.map(m => (
                        <tr key={m.id}>
                            <td className="mono">{formatDate(m.data)}</td>
                            {mostrarItem && <td className="nome">{m.item?.nome || "—"}</td>}
                            <td><span className={`est-chip ${m.tipo === "Entrada" ? "entrada" : "saida"}`}>{m.tipo}</span></td>
                            <td className="mono">{qtdComSinal(m, unidade || m.item?.unidade)}</td>
                            <td className="mono">{m.lote?.lote || "—"}</td>
                            <td style={{ minWidth: "220px" }}>{descreverMotivo(m)}</td>
                            <td style={{ whiteSpace: "nowrap" }}>{m.responsavel?.nome || "—"}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}

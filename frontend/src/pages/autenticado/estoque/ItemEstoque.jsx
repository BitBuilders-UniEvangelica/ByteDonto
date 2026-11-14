import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, Pencil } from "lucide-react";
import { useAuth } from "../../../context/AuthContext";
import { useFeedback } from "../../../hooks/useFeedback";
import { useRotas } from "../../../hooks/useRotas";
import { apiGetItemEstoque, apiGetFornecedores } from "../../../services/api";
import { formatDate } from "../../../utils/formatters";
import { EstadoErro } from "../../../components/feedback/Feedback";
import PaginaEstoque from "../../../components/estoque/PaginaEstoque";
import ModalItem from "../../../components/estoque/ModalItem";
import ModalEntrada from "../../../components/estoque/ModalEntrada";
import ModalSaida from "../../../components/estoque/ModalSaida";
import TabelaMovimentacoes from "../../../components/estoque/TabelaMovimentacoes";
import {
    CLASSE_STATUS, DIAS_ALERTA_VENCIMENTO, diasAte, formatQtd, statusLote,
} from "../../../components/estoque/estoqueUtils";

const COR_STATUS = { Normal: "var(--SuccessText)", "Estoque baixo": "#C2410C", Esgotado: "#BE123C" };

function Info({ rotulo, valor }) {
    return (
        <div>
            <dt>{rotulo}</dt>
            <dd>{valor || "—"}</dd>
        </div>
    );
}

export default function ItemEstoque() {
    const { id } = useParams();
    const { token } = useAuth();
    const { toast } = useFeedback();
    const navigate = useNavigate();
    const { rota } = useRotas();

    const [item, setItem] = useState(null);
    const [fornecedores, setFornecedores] = useState([]);
    const [erro, setErro] = useState(null); // "404" | "conexao"
    const [modal, setModal] = useState(null); // "editar" | "entrada" | "saida"

    function carregar() {
        if (!token) return;
        apiGetItemEstoque(token, id)
            .then(d => { setItem(d); setErro(null); })
            .catch(e => setErro(/não encontrado/i.test(e.message) ? "404" : "conexao"));
    }
    function carregarFornecedores() {
        if (!token) return;
        apiGetFornecedores(token).then(d => setFornecedores(Array.isArray(d) ? d : [])).catch(() => {});
    }

    // eslint-disable-next-line react-hooks/exhaustive-deps -- recarrega ao trocar de item
    useEffect(() => { carregar(); carregarFornecedores(); }, [token, id]);

    function aposSalvar(titulo, mensagem) {
        setModal(null);
        toast({ tipo: "sucesso", titulo, mensagem });
        carregar();
    }

    if (erro) {
        return (
            <PaginaEstoque>
                <Link className="est-voltar" to={rota("estoque")}><ArrowLeft size={16} strokeWidth={2} /> Voltar para Estoque</Link>
                <EstadoErro
                    tipo={erro === "404" ? "nao-encontrado" : "conexao"}
                    titulo={erro === "404" ? "Item não encontrado" : undefined}
                    mensagem={erro === "404" ? "Ele pode ter sido removido ou pertencer a outra clínica." : "Não foi possível carregar o item."}
                    textoBotao={erro === "404" ? "Voltar para Estoque" : "Tentar novamente"}
                    onAcao={erro === "404" ? () => navigate(rota("estoque")) : carregar}
                />
            </PaginaEstoque>
        );
    }

    if (!item) {
        return (
            <PaginaEstoque>
                <p className="est-vazio" style={{ padding: "6rem 1rem" }}>Carregando...</p>
            </PaginaEstoque>
        );
    }

    const diasVenc = diasAte(item.proximo_vencimento);
    const vencePerto = diasVenc !== null && diasVenc <= DIAS_ALERTA_VENCIMENTO;
    const subtitulo = [item.categoria, item.unidade, item.localizacao].filter(Boolean).join(" · ");

    return (
        <PaginaEstoque>
            {modal === "editar" && (
                <ModalItem
                    item={item}
                    fornecedores={fornecedores}
                    onFornecedorCriado={carregarFornecedores}
                    onFechar={() => setModal(null)}
                    onSalvo={() => aposSalvar("Item atualizado", item.nome)}
                />
            )}
            {modal === "entrada" && (
                <ModalEntrada
                    itens={[item]}
                    itemFixo={item}
                    fornecedores={fornecedores}
                    onFornecedorCriado={carregarFornecedores}
                    onFechar={() => setModal(null)}
                    onSalvo={() => aposSalvar("Entrada registrada", item.nome)}
                />
            )}
            {modal === "saida" && (
                <ModalSaida
                    itens={[item]}
                    itemFixo={item}
                    onFechar={() => setModal(null)}
                    onSalvo={() => aposSalvar("Saída registrada", item.nome)}
                />
            )}

            <div>
                <Link className="est-voltar" to={rota("estoque")}><ArrowLeft size={16} strokeWidth={2} /> Voltar para Estoque</Link>
                <div className="est-header">
                    <div style={{ minWidth: 0 }}>
                        <h1>{item.nome}{!item.ativo && <span className="est-chip esgotado" style={{ marginLeft: "10px", verticalAlign: "middle" }}>Removido</span>}</h1>
                        <p className="est-header-sub">{subtitulo}</p>
                    </div>
                    {item.ativo && (
                        <div className="est-acoes">
                            <button type="button" className="est-btn" onClick={() => setModal("editar")}><Pencil size={14} strokeWidth={2} /> Editar</button>
                            <button type="button" className="est-btn" onClick={() => setModal("saida")} disabled={item.quantidade_atual <= 0}>Registrar saída</button>
                            <button type="button" className="est-btn primario" onClick={() => setModal("entrada")}>Registrar entrada</button>
                        </div>
                    )}
                </div>
            </div>

            <div className="est-metricas">
                <div className="est-card">
                    <p className="est-metrica-rotulo">Quantidade atual</p>
                    <p className="est-metrica-valor" style={{ color: COR_STATUS[item.status] }}>
                        {formatQtd(item.quantidade_atual)}
                        <small>{item.unidade}</small>
                        <span className={`est-chip ${CLASSE_STATUS[item.status]}`}>{item.status}</span>
                    </p>
                </div>
                <div className="est-card">
                    <p className="est-metrica-rotulo">Estoque mínimo</p>
                    <p className="est-metrica-valor">
                        {formatQtd(item.estoque_minimo)}<small>{item.unidade}</small>
                    </p>
                </div>
                <div className="est-card">
                    <p className="est-metrica-rotulo">Próximo vencimento</p>
                    <p className="est-metrica-valor" style={vencePerto ? { color: diasVenc < 0 ? "#BE123C" : "#C2410C" } : undefined}>
                        {item.proximo_vencimento ? formatDate(item.proximo_vencimento) : "—"}
                        {item.proximo_vencimento && (
                            <span className={`est-chip ${statusLote(item.proximo_vencimento).classe}`}>
                                {diasVenc < 0 ? "Vencido" : diasVenc === 0 ? "Hoje" : `em ${diasVenc} ${diasVenc === 1 ? "dia" : "dias"}`}
                            </span>
                        )}
                    </p>
                </div>
            </div>

            <div className="est-grid-detalhe">
                <div className="est-card">
                    <p className="est-card-titulo">Informações</p>
                    <dl className="est-info">
                        <Info rotulo="Categoria" valor={item.categoria} />
                        <Info rotulo="Unidade" valor={item.unidade} />
                        <Info rotulo="Fornecedor principal" valor={item.fornecedor?.nome} />
                        <Info rotulo="Localização" valor={item.localizacao} />
                        <Info rotulo="Cadastrado em" valor={formatDate(item.created_at)} />
                        <Info rotulo="Observações" valor={item.observacoes} />
                    </dl>
                </div>

                <div className="est-card">
                    <p className="est-card-titulo">Lotes</p>
                    {item.lotes.length === 0 ? (
                        <p className="est-vazio">Nenhum lote com saldo. Registre uma entrada para repor o item.</p>
                    ) : (
                        <div className="est-tabela-wrap">
                            <table className="est-tabela">
                                <thead>
                                    <tr>
                                        <th>Lote</th>
                                        <th>Validade</th>
                                        <th>Quantidade</th>
                                        <th>Fornecedor</th>
                                        <th>Entrada</th>
                                        <th>Status</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {item.lotes.map(l => {
                                        const st = statusLote(l.validade);
                                        return (
                                            <tr key={l.id}>
                                                <td className="mono">{l.lote || "—"}</td>
                                                <td className="mono">{l.validade ? formatDate(l.validade) : "—"}</td>
                                                <td className="mono">{formatQtd(l.quantidade)} {item.unidade}</td>
                                                <td>{l.fornecedor?.nome || "—"}</td>
                                                <td className="mono">{formatDate(l.data_entrada)}</td>
                                                <td><span className={`est-chip ${st.classe}`}>{st.rotulo}</span></td>
                                            </tr>
                                        );
                                    })}
                                </tbody>
                            </table>
                        </div>
                    )}
                </div>
            </div>

            <div className="est-card">
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "0.75rem", marginBottom: "1rem", flexWrap: "wrap" }}>
                    <p className="est-card-titulo" style={{ margin: 0 }}>Últimas movimentações</p>
                    <button type="button" className="est-btn" onClick={() => navigate(rota(`estoque/historico?item=${item.id}`))}>Ver histórico completo</button>
                </div>
                <TabelaMovimentacoes movimentacoes={item.movimentacoes} unidade={item.unidade} />
            </div>
        </PaginaEstoque>
    );
}

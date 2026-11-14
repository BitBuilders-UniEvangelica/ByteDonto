import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Pencil, Trash2, TriangleAlert } from "lucide-react";
import { useAuth } from "../../../context/AuthContext";
import { useFeedback } from "../../../hooks/useFeedback";
import { useRotas } from "../../../hooks/useRotas";
import {
    apiGetItensEstoque, apiGetResumoEstoque, apiGetFornecedores, apiRemoverItemEstoque,
} from "../../../services/api";
import { Banner } from "../../../components/feedback/Feedback";
import PaginaEstoque from "../../../components/estoque/PaginaEstoque";
import ModalItem from "../../../components/estoque/ModalItem";
import ModalEntrada from "../../../components/estoque/ModalEntrada";
import ModalFornecedores from "../../../components/estoque/ModalFornecedores";
import { CLASSE_STATUS, formatQtd } from "../../../components/estoque/estoqueUtils";

const FILTROS = [
    { id: "todos", rotulo: "Todos" },
    { id: "Material", rotulo: "Materiais" },
    { id: "Insumo", rotulo: "Insumos" },
    { id: "baixo", rotulo: "Estoque baixo" },
];
const PERIODOS = [7, 30, 90];

const precisaRepor = (i) => i.status === "Esgotado" || i.status === "Estoque baixo";

/* ---- Itens mais consumidos (saídas no período) ---- */
function MaisConsumidos({ resumo, dias, onDias, carregando }) {
    const lista = resumo?.mais_consumidos || [];
    const max = Math.max(...lista.map(c => c.quantidade), 1);
    return (
        <div className="est-card">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "0.5rem", marginBottom: "1rem" }}>
                <p className="est-card-titulo" style={{ margin: 0 }}>Itens mais consumidos</p>
                <select className="est-select-pequeno" value={dias} onChange={e => onDias(Number(e.target.value))} aria-label="Período">
                    {PERIODOS.map(p => <option key={p} value={p}>Últimos {p} dias</option>)}
                </select>
            </div>
            {carregando ? (
                <p className="est-vazio">Carregando...</p>
            ) : lista.length === 0 ? (
                <p className="est-vazio">Nenhuma saída no período.</p>
            ) : (
                <div className="est-consumo">
                    {lista.map(c => (
                        <div key={c.item_id}>
                            <div className="est-consumo-linha">
                                <span>{c.nome}</span>
                                <span>{formatQtd(c.quantidade)} {c.unidade}</span>
                            </div>
                            <div className="est-barra"><div style={{ width: `${(c.quantidade / max) * 100}%` }} /></div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}

/* ---- Alerta de estoque (esgotados primeiro) ---- */
function AlertaEstoque({ itens, carregando, onAbrir }) {
    const alertas = itens
        .filter(precisaRepor)
        .sort((a, b) => (a.status === "Esgotado" ? 0 : 1) - (b.status === "Esgotado" ? 0 : 1) || a.nome.localeCompare(b.nome));
    return (
        <div className="est-card">
            <p className="est-card-titulo est-alerta-titulo"><TriangleAlert size={16} strokeWidth={2} /> Alerta de Estoque</p>
            {carregando ? (
                <p className="est-vazio">Carregando...</p>
            ) : alertas.length === 0 ? (
                <p className="est-vazio">Nenhum item abaixo do estoque mínimo.</p>
            ) : (
                <div className="est-alertas">
                    {alertas.map(i => (
                        <button key={i.id} type="button" className={`est-alerta ${i.status === "Esgotado" ? "esgotado" : ""}`} onClick={() => onAbrir(i)}>
                            <div className="est-alerta-topo">
                                <span>{i.nome}</span>
                                <span>{i.status}</span>
                            </div>
                            <div className="est-alerta-qtd">{formatQtd(i.quantidade_atual)}/{formatQtd(i.estoque_minimo)}</div>
                        </button>
                    ))}
                </div>
            )}
        </div>
    );
}

export default function Estoque() {
    const { token } = useAuth();
    const { toast, confirmar } = useFeedback();
    const navigate = useNavigate();
    const { rota } = useRotas();

    const [itens, setItens] = useState([]);
    const [fornecedores, setFornecedores] = useState([]);
    const [resumo, setResumo] = useState(null);
    const [dias, setDias] = useState(30);
    const [carregando, setCarregando] = useState(true);
    const [carregandoResumo, setCarregandoResumo] = useState(true);
    const [erroCarregar, setErroCarregar] = useState(false);

    const [busca, setBusca] = useState("");
    const [filtro, setFiltro] = useState("todos");
    const [modal, setModal] = useState(null); // { tipo: "item" | "entrada" | "fornecedores", item? }

    function carregarItens() {
        if (!token) return;
        setErroCarregar(false);
        return apiGetItensEstoque(token)
            .then(d => setItens(Array.isArray(d) ? d : []))
            .catch(() => setErroCarregar(true))
            .finally(() => setCarregando(false));
    }
    function carregarFornecedores() {
        if (!token) return;
        apiGetFornecedores(token).then(d => setFornecedores(Array.isArray(d) ? d : [])).catch(() => {});
    }
    function carregarResumo() {
        if (!token) return;
        apiGetResumoEstoque(token, dias)
            .then(setResumo)
            .catch(() => setResumo(null))
            .finally(() => setCarregandoResumo(false));
    }

    // eslint-disable-next-line react-hooks/exhaustive-deps -- carrega ao abrir a tela
    useEffect(() => { carregarItens(); carregarFornecedores(); }, [token]);
     
    useEffect(carregarResumo, [token, dias]);

    const filtrados = useMemo(() => {
        const termo = busca.trim().toLowerCase();
        return itens.filter(i => {
            if (termo && !i.nome.toLowerCase().includes(termo)) return false;
            if (filtro === "baixo") return precisaRepor(i);
            if (filtro !== "todos") return i.categoria === filtro;
            return true;
        });
    }, [itens, busca, filtro]);

    const abrirItem = (i) => navigate(rota(`estoque/item/${i.id}`));

    async function remover(item) {
        const ok = await confirmar({
            titulo: `Remover ${item.nome}?`,
            mensagem: "O item sai da lista do estoque. Lotes e histórico de movimentações ficam guardados.",
            acao: "Remover",
        });
        if (!ok) return;
        try {
            await apiRemoverItemEstoque(token, item.id);
            setItens(prev => prev.filter(i => i.id !== item.id));
            toast({ tipo: "sucesso", titulo: "Item removido", mensagem: item.nome });
        } catch (e) {
            toast({ tipo: "erro", titulo: "Não foi possível remover o item", mensagem: e.message });
        }
    }

    function aposSalvar(titulo, mensagem) {
        setModal(null);
        toast({ tipo: "sucesso", titulo, mensagem });
        carregarItens();
        carregarResumo();
    }

    const metricas = [
        { rotulo: "Total de itens", valor: itens.length },
        { rotulo: "Itens com estoque baixo", valor: itens.filter(precisaRepor).length, cor: "#C2410C" },
        { rotulo: "Movimentações no mês", valor: resumo?.movimentacoes_mes },
    ];

    return (
        <PaginaEstoque>
            {modal?.tipo === "item" && (
                <ModalItem
                    item={modal.item}
                    fornecedores={fornecedores}
                    onFornecedorCriado={carregarFornecedores}
                    onFechar={() => setModal(null)}
                    onSalvo={(salvo) => aposSalvar(modal.item ? "Item atualizado" : "Item adicionado", salvo.nome)}
                />
            )}
            {modal?.tipo === "entrada" && (
                <ModalEntrada
                    itens={itens}
                    fornecedores={fornecedores}
                    onFornecedorCriado={carregarFornecedores}
                    onFechar={() => setModal(null)}
                    onSalvo={() => aposSalvar("Entrada registrada", "O saldo do item foi atualizado.")}
                />
            )}
            {modal?.tipo === "fornecedores" && (
                <ModalFornecedores
                    fornecedores={fornecedores}
                    onAlterado={carregarFornecedores}
                    onFechar={() => setModal(null)}
                />
            )}

            <div className="est-header">
                <div>
                    <h1>Estoque</h1>
                    <p>Controle de produtos e materiais da clínica.</p>
                </div>
                <div className="est-acoes">
                    <button type="button" className="est-btn" onClick={() => setModal({ tipo: "fornecedores" })}>Fornecedores</button>
                    <button type="button" className="est-btn" onClick={() => navigate(rota("estoque/historico"))}>Histórico</button>
                    <button type="button" className="est-btn" onClick={() => setModal({ tipo: "entrada" })} disabled={itens.length === 0}>Nova entrada</button>
                    <button type="button" className="est-btn primario" onClick={() => setModal({ tipo: "item" })}>Novo Item</button>
                </div>
            </div>

            {erroCarregar && (
                <Banner texto="Não foi possível carregar o estoque." onTentarNovamente={carregarItens} />
            )}

            <div className="est-metricas">
                {metricas.map(m => (
                    <div key={m.rotulo} className="est-card">
                        <p className="est-metrica-rotulo">{m.rotulo}</p>
                        <p className="est-metrica-valor" style={m.cor && m.valor > 0 ? { color: m.cor } : undefined}>
                            {carregando || m.valor === undefined || m.valor === null ? "—" : m.valor}
                        </p>
                    </div>
                ))}
            </div>

            <div className="est-grid">
                <div className="est-card">
                    <div className="est-filtros">
                        <input
                            className="est-busca"
                            placeholder="Digite o nome"
                            value={busca}
                            onChange={e => setBusca(e.target.value)}
                            aria-label="Buscar item pelo nome"
                        />
                        <div className="est-abas" role="tablist">
                            {FILTROS.map(f => (
                                <button
                                    key={f.id}
                                    type="button"
                                    role="tab"
                                    aria-selected={filtro === f.id}
                                    className={`est-aba ${filtro === f.id ? "ativa" : ""}`}
                                    onClick={() => setFiltro(f.id)}
                                >
                                    {f.rotulo}
                                </button>
                            ))}
                        </div>
                    </div>

                    {carregando ? (
                        <p className="est-vazio" style={{ padding: "6rem 1rem" }}>Carregando...</p>
                    ) : filtrados.length === 0 ? (
                        <p className="est-vazio">
                            {itens.length === 0 ? "Nenhum item cadastrado. Clique em \"Novo Item\" para começar." : "Nenhum item encontrado com esses filtros."}
                        </p>
                    ) : (
                        <div className="est-tabela-wrap">
                            <table className="est-tabela">
                                <thead>
                                    <tr>
                                        <th>Item</th>
                                        <th>Categoria</th>
                                        <th className="num">Qtd. Atual</th>
                                        <th className="num">Estoque Mín.</th>
                                        <th className="num">Unidade</th>
                                        <th>Status</th>
                                        <th className="num">Ação</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {filtrados.map(i => (
                                        <tr key={i.id} className="clicavel" onClick={() => abrirItem(i)}>
                                            <td className="nome">{i.nome}</td>
                                            <td>{i.categoria}</td>
                                            <td className="num">{formatQtd(i.quantidade_atual)}</td>
                                            <td className="num">{formatQtd(i.estoque_minimo)}</td>
                                            <td className="num">{i.unidade}</td>
                                            <td><span className={`est-chip ${CLASSE_STATUS[i.status]}`}>{i.status}</span></td>
                                            <td className="acoes" onClick={e => e.stopPropagation()}>
                                                <button type="button" className="est-btn-icone" title="Editar" aria-label={`Editar ${i.nome}`} onClick={() => setModal({ tipo: "item", item: i })}>
                                                    <Pencil size={15} strokeWidth={2} />
                                                </button>
                                                <button type="button" className="est-btn-icone perigo" title="Remover" aria-label={`Remover ${i.nome}`} onClick={() => remover(i)}>
                                                    <Trash2 size={15} strokeWidth={2} />
                                                </button>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </div>

                <div className="est-lateral">
                    <MaisConsumidos resumo={resumo} dias={dias} onDias={setDias} carregando={carregandoResumo} />
                    <AlertaEstoque itens={itens} carregando={carregando} onAbrir={abrirItem} />
                </div>
            </div>
        </PaginaEstoque>
    );
}

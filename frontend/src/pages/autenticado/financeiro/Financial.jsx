/* IMPORTS */
import { useState, useEffect } from "react";
import { useAuth } from "../../../context/AuthContext";
import {
    apiGetFinanceiro,
    apiCriarLancamento,
    apiAtualizarLancamento,
    apiGetPacientesOpcoes,
    apiGetResumoFinanceiro,
    apiGetRepasses,
    apiGetEquipe,
} from "../../../services/api";
import Section from "../../../components/section/SectionAuth";
import SideBar from "../../../components/bar/SideBar";
import { useSidebar } from "../../../hooks/useSidebar";
import { useRotas } from "../../../hooks/useRotas";
import { formatCurrency, formatDate } from "../../../utils/formatters";
import { FilePlus, AlertTriangle } from "lucide-react";
import { useFeedback } from "../../../hooks/useFeedback";
import { Banner, BlocoCarregando } from "../../../components/feedback/Feedback";
import Paginacao from "../../../components/paginacao/Paginacao";
import "../../../styles/clinic.css";
import "../../../styles/Forms.css";

const FORMAS_PAGAMENTO = ["Dinheiro", "Cartão Débito", "Cartão Crédito", "Pix", "Convênio"];
const STATUS_OPTIONS = ["Pago", "Pendente", "Cancelado"];

const STATUS_STYLE = {
    Pago: { bg: "var(--SuccessBack)", color: "var(--SuccessText)" },
    Pendente: { bg: "var(--WarningBack)", color: "var(--WarningText)" },
    Cancelado: { bg: "var(--DangerBack)", color: "var(--DangerText)" },
};

const POR_PAGINA = 20;

const FORM_INICIAL = {
    paciente_id: "",
    dentista_responsavel: "",
    valor: "",
    descricao: "",
    forma_pagamento: "Dinheiro",
    status_pagamento: "Pendente",
};

/* ---- GRÁFICO A: Receita por mês (barras verticais) ---- */
/* receita: [{ mes: "AAAA-MM", pago }] — últimos 6 meses, somados no servidor */
function GraficoMensal({ receita }) {
    const meses = receita.map(({ mes, pago }) => {
        const [ano, m] = mes.split("-").map(Number);
        const label = new Date(ano, m - 1, 1).toLocaleDateString("pt-BR", { month: "short", year: "2-digit" });
        return { label, pago: Number(pago || 0) };
    });
    const max = Math.max(...meses.map(m => m.pago), 1);

    return (
        <div style={{ background: "var(--ThemeColor)", borderRadius: "14px", border: "1px solid var(--LineColor)", padding: "22px", flex: 1, boxShadow: "var(--shadow-sm)" }}>
            <p style={{ margin: "0 0 1.5rem 0", fontWeight: 700, fontSize: "14px", color: "var(--TextColor75)", textTransform: "uppercase", letterSpacing: "0.05em" }}>Receita Mensal (Pago)</p>
            <div style={{ display: "flex", alignItems: "flex-end", gap: "8px", height: "120px" }}>
                {meses.map((m, i) => (
                    <div key={i} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: "4px", height: "100%" }}>
                        <div style={{ flex: 1, width: "100%", display: "flex", alignItems: "flex-end" }}>
                            <div
                                title={formatCurrency(m.pago)}
                                style={{
                                    width: "100%",
                                    background: "var(--PrimaryColorsTheme)",
                                    borderRadius: "6px 6px 0 0",
                                    height: `${max > 0 ? Math.max((m.pago / max) * 100, m.pago > 0 ? 4 : 0) : 0}%`,
                                    transition: "height 0.4s",
                                    minHeight: m.pago > 0 ? "4px" : "0",
                                }}
                            />
                        </div>
                        <span style={{ fontSize: "10px", color: "var(--TextColor75)", fontWeight: 600, whiteSpace: "nowrap" }}>{m.label}</span>
                    </div>
                ))}
            </div>
        </div>
    );
}

/* ---- GRÁFICO B: Forma de pagamento (barras horizontais) ---- */
/* porForma: [{ forma, valor }] — total pago por forma, somado no servidor */
function GraficoFormas({ porForma }) {
    const entries = porForma.map(f => [f.forma, Number(f.valor || 0)]);
    const max = Math.max(...entries.map(e => e[1]), 1);
    const CORES = ["var(--PrimaryColors)", "var(--PrimaryColorsTheme)", "var(--SuccessText)", "var(--WarningText)", "var(--DangerText)", "var(--TextColor75)"];

    return (
        <div style={{ background: "var(--ThemeColor)", borderRadius: "14px", border: "1px solid var(--LineColor)", padding: "22px", flex: 1, boxShadow: "var(--shadow-sm)" }}>
            <p style={{ margin: "0 0 1.5rem 0", fontWeight: 700, fontSize: "14px", color: "var(--TextColor75)", textTransform: "uppercase", letterSpacing: "0.05em" }}>Forma de Pagamento</p>
            {entries.length === 0 ? (
                <p style={{ color: "var(--TextColor75)", fontSize: "14px" }}>Sem dados</p>
            ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                    {entries.map(([forma, valor], i) => (
                        <div key={forma}>
                            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "4px" }}>
                                <span style={{ fontSize: "13px", fontWeight: 600 }}>{forma}</span>
                                <span style={{ fontSize: "13px", fontWeight: 700, color: CORES[i % CORES.length] }}>
                                    {formatCurrency(valor)}
                                </span>
                            </div>
                            <div style={{ background: "var(--LineColor)", borderRadius: "4px", height: "8px" }}>
                                <div style={{ width: `${(valor / max) * 100}%`, height: "100%", background: CORES[i % CORES.length], borderRadius: "4px", transition: "width 0.4s" }} />
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}

/* ---- MAIN COMPONENT ---- */
/* Mesma tela em /owner/financial, /specialist/financial e /reception/financial.
   O repasse aos dentistas só aparece para o Dono. */
function Financial() {
    const { token } = useAuth();

    const { papel, estilo: sectionStyle } = useRotas();
    const isOwner = papel === "Dono";
    const opc_bar = useSidebar("financial");

    /* estados */
    const [listaPag, setListaPag] = useState({ items: [], total: 0, per_page: POR_PAGINA });
    const [pagina, setPagina] = useState(1);
    const [carregandoLista, setCarregandoLista] = useState(false);
    const [resumo, setResumo] = useState(null);
    const [pacientes, setPacientes] = useState([]);
    const [dentistas, setDentistas] = useState([]);
    const [loading, setLoading] = useState(true);
    const [erroCarregar, setErroCarregar] = useState(false);
    const { toast } = useFeedback();
    const [filtroStatus, setFiltroStatus] = useState("Todos");

    /* modal novo lançamento */
    const [showModal, setShowModal] = useState(false);
    const [form, setForm] = useState(FORM_INICIAL);
    const [enviando, setEnviando] = useState(false);
    const [erroForm, setErroForm] = useState(null);

    /* atualizando status inline */
    const [atualizando, setAtualizando] = useState(null); // id do lançamento em atualização

    /* repasses (mensal por dentista) */
    const [repasses, setRepasses] = useState(null);
    const [repassesMes, setRepassesMes] = useState(() => new Date().toISOString().slice(0, 7));
    const [repassesLoading, setRepassesLoading] = useState(false);

    /* Lista paginada: o servidor devolve só a página (20 lançamentos) já filtrada por status. */
    function carregarLista(page, status) {
        setCarregandoLista(true);
        return apiGetFinanceiro(token, { page, perPage: POR_PAGINA, status: status === "Todos" ? undefined : status })
            .then(d => setListaPag(d))
            .catch(() => setErroCarregar(true))
            .finally(() => setCarregandoLista(false));
    }

    /* Cards e gráficos: totais somados no servidor. */
    function carregarResumo() {
        return apiGetResumoFinanceiro(token)
            .then(r => setResumo(r))
            .catch(() => setErroCarregar(true));
    }

    /* fetch inicial */
    function carregar() {
        if (!token) return;
        setLoading(true);
        setErroCarregar(false);
        setPagina(1);
        Promise.all([
            carregarLista(1, filtroStatus),
            carregarResumo(),
            apiGetPacientesOpcoes(token).catch(() => []),
            apiGetEquipe(token).catch(() => []),
        ]).then(([, , p, e]) => {
            setPacientes(Array.isArray(p) ? p : []);
            // Só quem atende: Especialista e Dono (cirurgiões-dentistas).
            const equipe = Array.isArray(e) ? e : [];
            setDentistas(equipe.filter(m => m.papel === "Especialista" || m.papel === "Dono"));
        }).finally(() => setLoading(false));
    }

    // Carga inicial só quando o token muda; filtro e página recarregam pelos handlers.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    useEffect(carregar, [token]);

    function mudarFiltro(status) {
        setFiltroStatus(status);
        setPagina(1);
        carregarLista(1, status);
    }

    function mudarPagina(page) {
        setPagina(page);
        carregarLista(page, filtroStatus);
    }

    /* fetch repasses quando o mês muda (apenas para o Owner) */
    useEffect(() => {
        if (!token || !isOwner) return;
        setRepassesLoading(true);
        apiGetRepasses(token, repassesMes)
            .then(data => setRepasses(data))
            .catch(() => setRepasses({ mes: repassesMes, itens: [] }))
            .finally(() => setRepassesLoading(false));
    }, [token, repassesMes, isOwner]);

    /* métricas (somadas no servidor) */
    const totalPago = resumo?.pago_mes ?? 0;
    const totalPendente = resumo?.pendente_mes ?? 0;
    const totalLancamentos = resumo?.total_lancamentos ?? listaPag.total ?? 0;
    const filtrados = listaPag.items || [];

    /* handlers */
    function abrirModal() {
        setForm(FORM_INICIAL);
        setErroForm(null);
        setShowModal(true);
    }

    async function handleCriar(e) {
        e.preventDefault();
        if (!form.paciente_id) {
            setErroForm("Selecione o paciente do lançamento.");
            return;
        }
        if (!form.valor || Number(form.valor) <= 0) {
            setErroForm("Informe um valor válido.");
            return;
        }
        setEnviando(true);
        setErroForm(null);
        try {
            await apiCriarLancamento(token, {
                paciente_id: form.paciente_id,
                dentista_responsavel: form.dentista_responsavel || undefined,
                valor: Number(form.valor),
                descricao: form.descricao || undefined,
                forma_pagamento: form.forma_pagamento,
                status_pagamento: form.status_pagamento,
            });
            const paciente = pacientes.find(p => p.id === form.paciente_id);
            // Recarrega a primeira página e os totais (o novo lançamento é o mais recente).
            setPagina(1);
            carregarLista(1, filtroStatus);
            carregarResumo();
            setShowModal(false);
            toast({
                tipo: "sucesso",
                titulo: "Lançamento salvo",
                mensagem: [formatCurrency(Number(form.valor)), paciente?.nome, form.status_pagamento].filter(Boolean).join(" · "),
            });
        } catch (err) {
            setErroForm(err.message);
        } finally {
            setEnviando(false);
        }
    }

    async function marcarComoPago(id) {
        setAtualizando(id);
        try {
            await apiAtualizarLancamento(token, id, { status_pagamento: "Pago" });
            carregarLista(pagina, filtroStatus);
            carregarResumo();
            toast({ tipo: "sucesso", titulo: "Pagamento registrado", mensagem: "O lançamento foi marcado como pago." });
        } catch (err) {
            console.error("Erro ao atualizar lançamento", err);
            toast({ tipo: "erro", titulo: "Não foi possível atualizar o lançamento", mensagem: err.message || "Tente novamente em instantes." });
        } finally {
            setAtualizando(null);
        }
    }

    return (
        <>
            <Section type_styles={sectionStyle} />
            <SideBar opc={opc_bar} styles={sectionStyle} />

            <main className={`mainBar ${sectionStyle}`} style={{ position: "relative" }}>

                {/* ---- MODAL NOVO LANÇAMENTO ---- */}
                {showModal && (
                    <div className="modal-overlay" style={{ zIndex: 9999 }}>
                        <div className="modal-caixa" style={{ background: "var(--ThemeColor)", padding: "2rem", borderRadius: "16px", width: "100%", maxWidth: "600px", boxShadow: "0 20px 40px -12px rgba(15,23,42,0.2)", animation: "fadeIn 0.2s", border: "1px solid var(--LineColor)" }}>
                            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "2rem" }}>
                                <div>
                                    <span style={{ background: "var(--PrimaryColorsBack)", color: "var(--PrimaryColorsTheme)", padding: "6px 12px", borderRadius: "8px", fontSize: "12px", fontWeight: 800, marginBottom: "12px", display: "inline-block", textTransform: "uppercase", letterSpacing: "0.04em" }}>Novo Registro</span>
                                    <h2 style={{ color: "var(--TextColor)", margin: 0, fontSize: "24px" }}>Novo Lançamento</h2>
                                    <p style={{ color: "var(--TextColor75)", margin: "8px 0 0 0" }}>Registre um novo movimento financeiro.</p>
                                </div>
                            </div>

                            <form onSubmit={handleCriar} className="forms-section" style={{ padding: 0 }}>
                                {erroForm && (
                                    <div style={{ background: "var(--DangerBack)", color: "var(--DangerText)", padding: "10px 14px", borderRadius: "8px", marginBottom: "1rem", fontSize: "14px", display: "flex", alignItems: "center", gap: "8px" }}>
                                        <AlertTriangle size={16} strokeWidth={2} /> {erroForm}
                                    </div>
                                )}

                                <div className="field" style={{ marginBottom: "1rem" }}>
                                    <label>Paciente *</label>
                                    <select style={{ width: "100%" }} required value={form.paciente_id} onChange={e => setForm(p => ({ ...p, paciente_id: e.target.value }))}>
                                        <option value="">Selecione o paciente...</option>
                                        {pacientes.map(p => (
                                            <option key={p.id} value={p.id}>{p.nome}</option>
                                        ))}
                                    </select>
                                </div>

                                <div className="field" style={{ marginBottom: "1rem" }}>
                                    <label>Dentista responsável</label>
                                    <select style={{ width: "100%" }} value={form.dentista_responsavel} onChange={e => setForm(p => ({ ...p, dentista_responsavel: e.target.value }))}>
                                        <option value="">Selecione (opcional)...</option>
                                        {dentistas.map(d => (
                                            <option key={d.id} value={d.id}>{d.nome}</option>
                                        ))}
                                    </select>
                                </div>

                                <div className="flex-inpus" style={{ display: "flex", gap: "1rem" }}>
                                    <div className="field" style={{ flex: 1 }}>
                                        <label>Valor (R$) *</label>
                                        <input type="number" min="0" step="0.01" required placeholder="0,00" style={{ width: "100%" }} value={form.valor} onChange={e => setForm(p => ({ ...p, valor: e.target.value }))} />
                                    </div>
                                    <div className="field" style={{ flex: 1 }}>
                                        <label>Forma de Pagamento</label>
                                        <select style={{ width: "100%" }} value={form.forma_pagamento} onChange={e => setForm(p => ({ ...p, forma_pagamento: e.target.value }))}>
                                            {FORMAS_PAGAMENTO.map(f => <option key={f} value={f}>{f}</option>)}
                                        </select>
                                    </div>
                                </div>

                                <div className="field" style={{ marginBottom: "1rem" }}>
                                    <label>Status</label>
                                    <select style={{ width: "100%" }} value={form.status_pagamento} onChange={e => setForm(p => ({ ...p, status_pagamento: e.target.value }))}>
                                        <option value="Pago">Pago</option>
                                        <option value="Pendente">Pendente</option>
                                    </select>
                                </div>

                                <div className="field" style={{ marginBottom: 0 }}>
                                    <label>Descrição do procedimento</label>
                                    <input
                                        type="text"
                                        placeholder='Ex: "Restauração dente 36" — aparece no extrato do paciente'
                                        style={{ width: "100%" }}
                                        value={form.descricao}
                                        onChange={e => setForm(p => ({ ...p, descricao: e.target.value }))}
                                    />
                                </div>

                                <div style={{ display: "flex", justifyContent: "flex-end", gap: "1rem", borderTop: "1px solid var(--LineColor)", paddingTop: "1.5rem", marginTop: "2rem" }}>
                                    <button type="button" onClick={() => setShowModal(false)} className="submit" style={{ padding: "14px 24px", background: "var(--BackColor)", color: "var(--TextColor)", boxShadow: "none" }} disabled={enviando}>Cancelar</button>
                                    <button type="submit" className="submit" style={{ padding: "14px 36px", background: "var(--PrimaryColorsTheme)" }} disabled={enviando}>
                                        {enviando ? "Salvando..." : "Salvar Lançamento"}
                                    </button>
                                </div>
                            </form>
                        </div>
                    </div>
                )}
                {/* ---- FIM MODAL ---- */}

                {/* ---- HEADER ---- */}
                <div className="page-header" style={{ marginBottom: "0.5rem" }}>
                    <div>
                        <h1  style={{ margin: '0 0 0.5rem 0', color: 'var(--PrimaryColorsTheme)', fontSize: '28px' }}>Financeiro</h1>
                        <p className="text75 page-header-desc">Controle de lançamentos, recebimentos e pendências.</p>
                    </div>
                    <button onClick={abrirModal} style={{ background: "var(--PrimaryColorsTheme)", color: "white", padding: "12px 24px", borderRadius: "12px", fontWeight: 700, display: "flex", alignItems: "center", gap: "0.5rem", border: "none", cursor: "pointer", boxShadow: "var(--shadow-sm)" }}>
                        <FilePlus size={18} strokeWidth={2} /> Novo Lançamento
                    </button>
                </div>

                {erroCarregar && (
                    <Banner
                        texto="Não foi possível carregar os lançamentos. Os valores abaixo podem estar incompletos."
                        onTentarNovamente={carregar}
                    />
                )}

                {/* ---- CARDS DE MÉTRICAS ---- */}
                <div className="fin-metricas">
                    <div style={{ background: "var(--ThemeColor)", borderRadius: "14px", border: "1px solid var(--LineColor)", padding: "22px", boxShadow: "var(--shadow-sm)" }}>
                        <p style={{ margin: "0 0 0.25rem 0", fontSize: "13px", fontWeight: 700, color: "var(--TextColor75)", textTransform: "uppercase", letterSpacing: "0.05em" }}>Total Pago no Mês</p>
                        <p style={{ margin: 0, fontSize: "28px", fontWeight: 800, color: "var(--SuccessText)", fontFamily: "var(--font-secondary)" }}>
                            {loading ? "—" : formatCurrency(totalPago)}
                        </p>
                    </div>
                    <div style={{ background: "var(--ThemeColor)", borderRadius: "14px", border: "1px solid var(--LineColor)", padding: "22px", boxShadow: "var(--shadow-sm)" }}>
                        <p style={{ margin: "0 0 0.25rem 0", fontSize: "13px", fontWeight: 700, color: "var(--TextColor75)", textTransform: "uppercase", letterSpacing: "0.05em" }}>Total Pendente</p>
                        <p style={{ margin: 0, fontSize: "28px", fontWeight: 800, color: "var(--WarningText)", fontFamily: "var(--font-secondary)" }}>
                            {loading ? "—" : formatCurrency(totalPendente)}
                        </p>
                    </div>
                    <div style={{ background: "var(--ThemeColor)", borderRadius: "14px", border: "1px solid var(--LineColor)", padding: "22px", boxShadow: "var(--shadow-sm)" }}>
                        <p style={{ margin: "0 0 0.25rem 0", fontSize: "13px", fontWeight: 700, color: "var(--TextColor75)", textTransform: "uppercase", letterSpacing: "0.05em" }}>Total de Lançamentos</p>
                        <p style={{ margin: 0, fontSize: "28px", fontWeight: 800, color: "var(--PrimaryColorsTheme)", fontFamily: "var(--font-secondary)" }}>
                            {loading ? "—" : totalLancamentos}
                        </p>
                    </div>
                </div>

                {/* ---- GRÁFICOS ---- */}
                {!loading && resumo && resumo.total_lancamentos > 0 && (
                    <div className="fin-graficos">
                        <GraficoMensal receita={resumo.receita_mensal || []} />
                        <GraficoFormas porForma={resumo.por_forma || []} />
                    </div>
                )}

                {/* ---- REPASSES POR DENTISTA (somente Owner) ---- */}
                {isOwner && (
                    <div className="camp-clinic camp-register camp-compact">
                        <div className="fin-repasse-header">
                            <div>
                                <h2 style={{ margin: 0 }}>Repasse aos Dentistas</h2>
                                <p className="text75" style={{ margin: "4px 0 0 0", fontSize: "13px" }}>Apenas valores PAGOS no mês entram no cálculo. Configure o % de cada um em Equipe.</p>
                            </div>
                            <input
                                type="month"
                                value={repassesMes}
                                onChange={e => setRepassesMes(e.target.value)}
                                style={{ padding: "8px 12px", border: "1px solid var(--LineColor)", borderRadius: "10px", fontSize: "14px" }}
                            />
                        </div>

                        {repassesLoading ? (
                            <BlocoCarregando />
                        ) : !repasses?.itens?.length ? (
                            <p className="text75" style={{ textAlign: "center", padding: "1.5rem" }}>Nenhum dentista com produção no mês.</p>
                        ) : (
                            <div className="table">
                                <div className="table-header grid-repasse">
                                    <p className="text75">Dentista</p>
                                    <p className="text75">%</p>
                                    <p className="text75 hide-mobile">Produção (Pago)</p>
                                    <p className="text75" style={{ textAlign: "right" }}>Repasse</p>
                                </div>
                                <div className="table-body">
                                    {repasses.itens.map((r, idx) => (
                                        <div
                                            key={r.dentista_id}
                                            className="table-row grid-repasse"
                                            style={{ borderBottom: idx === repasses.itens.length - 1 ? "none" : "1px solid var(--LineColor)" }}
                                        >
                                            <p style={{ fontWeight: 600 }}>{r.dentista_nome}</p>
                                            <p style={{ fontWeight: 600 }}>{r.percentual_repasse}%</p>
                                            <p className="hide-mobile" style={{ fontFamily: "var(--font-secondary)" }}>{formatCurrency(r.producao)}</p>
                                            <p style={{ fontFamily: "var(--font-secondary)", fontWeight: 700, color: "var(--SuccessText)", textAlign: "right" }}>
                                                {formatCurrency(r.repasse)}
                                            </p>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>
                )}

                {/* ---- FILTROS ---- */}
                <div className="fin-filtros">
                    {["Todos", ...STATUS_OPTIONS].map(s => (
                        <button
                            key={s}
                            onClick={() => mudarFiltro(s)}
                            style={{
                                padding: "8px 18px",
                                borderRadius: "10px",
                                border: "1px solid var(--LineColor)",
                                cursor: "pointer",
                                fontWeight: 600,
                                fontSize: "14px",
                                background: filtroStatus === s ? "var(--PrimaryColorsTheme)" : "white",
                                color: filtroStatus === s ? "white" : "var(--TextColor75)",
                                transition: "all 0.15s",
                            }}
                        >
                            {s}
                        </button>
                    ))}
                </div>

                {/* ---- TABELA ---- */}
                <div className="camp-clinic camp-register camp-compact">
                    <h2 style={{ margin: "0 0 1.5rem 0" }}>Lançamentos</h2>

                    {loading ? (
                        <BlocoCarregando />
                    ) : filtrados.length === 0 ? (
                        <p className="text75" style={{ textAlign: "center", padding: "2rem" }}>Nenhum lançamento encontrado.</p>
                    ) : (
                        <div className="table">
                            <div className="table-header grid-lancamentos">
                                <p className="text75 hide-mobile">Data</p>
                                <p className="text75">Paciente</p>
                                <p className="text75 hide-mobile">Dentista</p>
                                <p className="text75 hide-mobile">Procedimento</p>
                                <p className="text75 hide-mobile">Pagamento</p>
                                <p className="text75">Valor</p>
                                <p className="text75 hide-mobile">Status</p>
                                <p className="text75" style={{ textAlign: "right" }}>Ações</p>
                            </div>
                            <div className="table-body">
                                {filtrados.map((l, idx) => {
                                    const st = STATUS_STYLE[l.status_pagamento] || STATUS_STYLE["Pendente"];
                                    return (
                                        <div
                                            key={l.id}
                                            className="table-row grid-lancamentos"
                                            style={{ borderBottom: idx === filtrados.length - 1 ? "none" : "1px solid var(--LineColor)" }}
                                        >
                                            <p className="hide-mobile" style={{ fontFamily: "var(--font-secondary)", fontSize: "13px", fontWeight: 500 }}>{formatDate(l.created_at)}</p>
                                            <div style={{ minWidth: 0 }}>
                                                <p style={{ fontWeight: 600 }}>{l.pacientes?.nome || "—"}</p>
                                                {/* No celular a data vai embaixo do nome */}
                                                <span className="show-mobile text75" style={{ fontSize: "12px" }}>{formatDate(l.created_at)}</span>
                                            </div>
                                            <p className="text75 hide-mobile">{l.dentista?.nome || "—"}</p>
                                            <p className="text75 hide-mobile" style={{ fontSize: "13px" }}>{l.descricao || "—"}</p>
                                            <p className="text75 hide-mobile">{l.forma_pagamento || "—"}</p>
                                            <div>
                                                <p style={{ fontFamily: "var(--font-secondary)", fontWeight: 700 }}>{formatCurrency(l.valor)}</p>
                                                {/* No celular o status vai embaixo do valor */}
                                                <span className="show-mobile" style={{ background: st.bg, color: st.color, padding: "2px 8px", borderRadius: "6px", fontSize: "11px", fontWeight: 700, width: "fit-content", marginTop: "4px" }}>
                                                    {l.status_pagamento}
                                                </span>
                                            </div>
                                            <span className="hide-mobile" style={{ background: st.bg, color: st.color, padding: "4px 10px", borderRadius: "8px", fontSize: "12px", fontWeight: 700, whiteSpace: "nowrap", alignSelf: "center" }}>
                                                {l.status_pagamento}
                                            </span>
                                            <div style={{ textAlign: "right" }}>
                                                {l.status_pagamento === "Pendente" && (
                                                    <button
                                                        onClick={() => marcarComoPago(l.id)}
                                                        disabled={atualizando === l.id}
                                                        className="submit"
                                                        style={{ padding: "6px 12px", fontSize: "12px", borderRadius: "8px", background: "var(--PrimaryColorsTheme)", color: "white", border: "none", boxShadow: "none", whiteSpace: "nowrap" }}
                                                    >
                                                        {atualizando === l.id ? "..." : "Marcar Pago"}
                                                    </button>
                                                )}
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    )}
                    <Paginacao
                        page={pagina}
                        perPage={listaPag.per_page || POR_PAGINA}
                        total={listaPag.total || 0}
                        onMudarPagina={mudarPagina}
                        carregando={carregandoLista}
                        rotulo="lançamentos"
                    />
                </div>
            </main>
        </>
    );
}

export default Financial;

/* IMPORTS */
import { useState, useEffect } from "react";
import { useAuth } from "../../context/AuthContext";
import { apiGetConsultas, apiGetMetricas, apiAtualizarConsulta } from "../../services/api";
import Section from "../../components/section/SectionAuth";
import SideBar from "../../components/bar/SideBar";
import { useSpecialistSidebar } from "../../hooks/useSidebar";
import { CalendarDays, Users, ChevronLeft, ChevronRight, X } from "lucide-react";
import "../../styles/clinic.css";
import "../../styles/Forms.css";

/* ---- helpers de data ---- */
function getMondayOfWeek(date) {
    const d = new Date(date);
    const day = d.getDay(); // 0=Dom
    const diff = day === 0 ? -6 : 1 - day;
    d.setDate(d.getDate() + diff);
    d.setHours(0, 0, 0, 0);
    return d;
}

function isSameDay(a, b) {
    return (
        a.getFullYear() === b.getFullYear() &&
        a.getMonth() === b.getMonth() &&
        a.getDate() === b.getDate()
    );
}

function getHourFromISO(iso) {
    if (!iso) return -1;
    const d = new Date(iso);
    return d.getHours();
}

const DIAS_SEMANA = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"];
const HORAS = Array.from({ length: 14 }, (_, i) => i + 7); // 07 .. 20

const STATUS_BADGE = {
    Agendado: { bg: "var(--PrimaryColorsBack)", color: "var(--PrimaryColorsTheme)" },
    Finalizado: { bg: "var(--SuccessBack)", color: "var(--SuccessText)" },
    Cancelado: { bg: "var(--DangerBack)", color: "var(--DangerText)" },
};

/* ---- CALENDAR WEEK COMPONENT ---- */
function CalendarWeek({ consultas, semanaBase, onMudarSemana }) {
    const dias = Array.from({ length: 7 }, (_, i) => {
        const d = new Date(semanaBase);
        d.setDate(semanaBase.getDate() + i);
        return d;
    });

    const consultasDoDia = (dia) =>
        consultas.filter(c => {
            const d = new Date(c.data_agendada);
            return d.toDateString() === dia.toDateString();
        });

    const STATUS_COR = {
        Agendado: { bg: "var(--PrimaryColorsBack)", color: "var(--PrimaryColorsTheme)" },
        Finalizado: { bg: "var(--SuccessBack)", color: "var(--SuccessText)" },
        Cancelado: { bg: "var(--DangerBack)", color: "var(--DangerText)" },
        Faltou: { bg: "var(--BackColor)", color: "var(--TextColor75)" },
    };

    const NOMES_DIAS = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sab"];

    return (
        <div style={{ background: "var(--ThemeColor)", borderRadius: "var(--radius-lg)", border: "1px solid var(--LineColor)", padding: "1.5rem", marginBottom: "0.5rem", boxShadow: "var(--shadow-sm)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
                <h3 style={{ margin: 0, color: "var(--TextColor)", fontSize: "16px", fontWeight: 700, display: "flex", alignItems: "center", gap: "0.5rem" }}>
                    <CalendarDays size={18} strokeWidth={2} /> Visão Semanal
                </h3>
                <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
                    <button
                        aria-label="Semana anterior"
                        onClick={() => onMudarSemana(-7)}
                        style={{ background: "var(--BackColor)", border: "1px solid var(--LineColor)", borderRadius: "var(--radius-sm)", padding: "6px 8px", cursor: "pointer", color: "var(--TextColor75)", display: "flex", alignItems: "center" }}
                    >
                        <ChevronLeft size={18} strokeWidth={2} />
                    </button>
                    <span style={{ fontSize: "13px", color: "var(--TextColor75)", fontWeight: 600 }}>
                        {dias[0].toLocaleDateString("pt-BR", { day: "2-digit", month: "short" })}
                        {" — "}
                        {dias[6].toLocaleDateString("pt-BR", { day: "2-digit", month: "short", year: "numeric" })}
                    </span>
                    <button
                        aria-label="Próxima semana"
                        onClick={() => onMudarSemana(7)}
                        style={{ background: "var(--BackColor)", border: "1px solid var(--LineColor)", borderRadius: "var(--radius-sm)", padding: "6px 8px", cursor: "pointer", color: "var(--TextColor75)", display: "flex", alignItems: "center" }}
                    >
                        <ChevronRight size={18} strokeWidth={2} />
                    </button>
                </div>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(7, 1fr)", gap: "6px" }}>
                {dias.map((dia, i) => {
                    const consultasDia = consultasDoDia(dia);
                    const hoje = new Date().toDateString() === dia.toDateString();
                    return (
                        <div
                            key={i}
                            style={{
                                minHeight: "90px",
                                borderRadius: "var(--radius-md)",
                                border: `1px solid ${hoje ? "var(--PrimaryColorsTheme)" : "var(--LineColor)"}`,
                                padding: "8px",
                                background: hoje ? "var(--PrimaryColorsBack)" : "var(--ThemeColor)",
                            }}
                        >
                            <p style={{ margin: "0 0 6px 0", fontSize: "11px", fontWeight: 700, color: hoje ? "var(--PrimaryColorsTheme)" : "var(--TextColor75)", textAlign: "center" }}>
                                {NOMES_DIAS[dia.getDay()]}
                                <br />
                                <span style={{ fontSize: "16px", color: hoje ? "var(--PrimaryColorsTheme)" : "var(--TextColor)" }}>
                                    {dia.getDate()}
                                </span>
                            </p>
                            {consultasDia.slice(0, 3).map((c, j) => {
                                const cor = STATUS_COR[c.status] || STATUS_COR["Agendado"];
                                return (
                                <div
                                    key={j}
                                    style={{
                                        fontSize: "10px",
                                        fontWeight: 600,
                                        background: cor.bg,
                                        color: cor.color,
                                        borderRadius: "999px",
                                        padding: "2px 8px",
                                        marginBottom: "3px",
                                        overflow: "hidden",
                                        whiteSpace: "nowrap",
                                        textOverflow: "ellipsis",
                                    }}
                                >
                                    {new Date(c.data_agendada).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })}{" "}
                                    {c.pacientes?.nome?.split(" ")[0] || "—"}
                                </div>
                                );
                            })}
                            {consultasDia.length > 3 && (
                                <p style={{ fontSize: "10px", color: "var(--TextColor75)", margin: "2px 0 0 0" }}>
                                    +{consultasDia.length - 3}
                                </p>
                            )}
                        </div>
                    );
                })}
            </div>
        </div>
    );
}

/* ---- MAIN COMPONENT ---- */
function SpecialistDashboard() {
    const { token } = useAuth();

    /* sidebar */
    const opc_bar = useSpecialistSidebar("agenda");

    /* semana */
    const monday = getMondayOfWeek(new Date());
    const weekDates = DIAS_SEMANA.map((label, i) => {
        const d = new Date(monday);
        d.setDate(monday.getDate() + i);
        return { label, date: d };
    });

    const [dataSelecionada, setDataSelecionada] = useState(new Date());
    const [consultas, setConsultas] = useState([]);
    const [loadingConsultas, setLoadingConsultas] = useState(false);
    const [metricas, setMetricas] = useState(null);
    const [semanaBase, setSemanaBase] = useState(() => {
        const d = new Date();
        d.setDate(d.getDate() - d.getDay()); // inicio da semana (domingo)
        d.setHours(0, 0, 0, 0);
        return d;
    });

    /* modal encerrar */
    const [showEncerrar, setShowEncerrar] = useState(false);
    const [activePatient, setActivePatient] = useState("");
    const [consultaAtiva, setConsultaAtiva] = useState(null);
    const [procedimentos, setProcedimentos] = useState("");
    const [evolucao, setEvolucao] = useState("");
    const [salvandoEncerrar, setSalvandoEncerrar] = useState(false);
    const [erroEncerrar, setErroEncerrar] = useState("");

    /* fetch consultas quando data muda */
    const carregarConsultas = () => {
        if (!token) return;
        setLoadingConsultas(true);
        apiGetConsultas(token)
            .then(data => setConsultas(Array.isArray(data) ? data : []))
            .catch(err => console.error("Erro ao carregar consultas", err))
            .finally(() => setLoadingConsultas(false));
    };

    useEffect(() => {
        carregarConsultas();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [token, dataSelecionada]);

    /* abrir modal de encerramento */
    function abrirEncerrar(consulta) {
        setConsultaAtiva(consulta);
        setActivePatient(consulta.pacientes?.nome || consulta.paciente?.nome || "Paciente");
        setProcedimentos(consulta.procedimentos_descritos || "");
        setEvolucao(consulta.evolucao_clinica || "");
        setErroEncerrar("");
        setShowEncerrar(true);
    }

    /* salvar encerramento */
    async function salvarEncerramento() {
        if (!consultaAtiva) return;
        setErroEncerrar("");
        setSalvandoEncerrar(true);
        try {
            await apiAtualizarConsulta(token, consultaAtiva.id, {
                procedimentos_descritos: procedimentos,
                evolucao_clinica: evolucao,
                status: "Finalizado",
            });
            setShowEncerrar(false);
            setConsultaAtiva(null);
            carregarConsultas();
        } catch (err) {
            console.error("Erro ao encerrar consulta", err);
            setErroEncerrar(err.message || "Não foi possível salvar o atendimento.");
        } finally {
            setSalvandoEncerrar(false);
        }
    }

    /* fetch métricas uma vez */
    useEffect(() => {
        if (!token) return;
        apiGetMetricas(token)
            .then(data => setMetricas(data))
            .catch(err => console.error("Erro ao carregar métricas", err));
    }, [token]);

    /* filtrar consultas pelo dia selecionado */
    const consultasDoDia = consultas.filter(c => {
        if (!c.data_agendada) return false;
        const d = new Date(c.data_agendada);
        return isSameDay(d, dataSelecionada);
    });

    /* mapear consulta por hora */
    function consultaNoSlot(hora) {
        return consultasDoDia.find(c => getHourFromISO(c.data_agendada) === hora) || null;
    }

    /* formatar data legível */
    const dataFormatada = dataSelecionada.toLocaleDateString("pt-BR", {
        weekday: "long", day: "numeric", month: "long",
    });

    return (
        <>
            <Section type_styles="specialist" />
            <SideBar opc={opc_bar} styles="specialist" />

            <main className="mainBar specialist" style={{ position: "relative" }}>

                {/* ---- MODAL ENCERRAR ATENDIMENTO ---- */}
                {showEncerrar && (
                    <div style={{ position: "fixed", top: 0, left: 0, width: "100vw", height: "100vh", background: "rgba(15,23,42,0.4)", backdropFilter: "blur(8px)", zIndex: 1000, display: "flex", justifyContent: "center", alignItems: "center" }}>
                        <div style={{ background: "var(--ThemeColor)", padding: "2.5rem", borderRadius: "var(--radius-lg)", width: "100%", maxWidth: "600px", boxShadow: "var(--shadow-md)", animation: "fadeIn 0.2s", border: "1px solid var(--LineColor)" }}>
                            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "2rem" }}>
                                <div>
                                    <span className="ui-label" style={{ background: "var(--PrimaryColorsBack)", color: "var(--PrimaryColorsTheme)", padding: "6px 12px", borderRadius: "var(--radius-sm)", marginBottom: "12px", display: "inline-block" }}>ENCERRAR CONSULTA</span>
                                    <h2 className="section" style={{ color: "var(--TextColor)", margin: "8px 0 0 0", fontSize: "24px" }}>Resumo do Atendimento</h2>
                                    <p style={{ color: "var(--TextColor75)", margin: "8px 0 0 0" }}>Paciente: <strong style={{ color: "var(--PrimaryColorsTheme)" }}>{activePatient}</strong></p>
                                </div>
                                <button aria-label="Fechar" onClick={() => setShowEncerrar(false)} style={{ background: "var(--BackColor)", border: "1px solid var(--LineColor)", width: "40px", height: "40px", borderRadius: "50%", cursor: "pointer", color: "var(--TextColor75)", display: "flex", alignItems: "center", justifyContent: "center" }}><X size={18} strokeWidth={2} /></button>
                            </div>

                            <div className="forms-section" style={{ padding: 0 }}>
                                <div className="field" style={{ marginBottom: "1rem" }}>
                                    <label>Procedimentos Realizados Hoje *</label>
                                    <input
                                        type="text"
                                        placeholder="Ex: Avaliação de Rotina, Limpeza (Profilaxia)..."
                                        style={{ width: "100%" }}
                                        value={procedimentos}
                                        onChange={(e) => setProcedimentos(e.target.value)}
                                    />
                                </div>
                                <div className="field" style={{ marginBottom: 0 }}>
                                    <label>Evolução Clínica (Anotações do Prontuário Central) *</label>
                                    <textarea
                                        rows="3"
                                        placeholder="Descreva tecnicamente o que foi feito, materiais usados e observações médicas..."
                                        style={{ width: "100%" }}
                                        value={evolucao}
                                        onChange={(e) => setEvolucao(e.target.value)}
                                    ></textarea>
                                </div>
                            </div>

                            {erroEncerrar && (
                                <p style={{ color: "var(--DangerText)", background: "var(--DangerBack)", padding: "10px 14px", borderRadius: "var(--radius-sm)", fontSize: "14px", margin: "1.5rem 0 0 0" }}>{erroEncerrar}</p>
                            )}

                            <div style={{ display: "flex", justifyContent: "flex-end", gap: "1rem", borderTop: "1px solid var(--LineColor)", paddingTop: "1.5rem", marginTop: "2rem" }}>
                                <button onClick={() => setShowEncerrar(false)} className="submit" style={{ padding: "14px 24px", background: "var(--BackColor)", color: "var(--TextColor)", boxShadow: "none" }}>Continuar Atendendo</button>
                                <button
                                    className="submit"
                                    onClick={salvarEncerramento}
                                    disabled={salvandoEncerrar}
                                    style={{ padding: "14px 40px", background: "var(--PrimaryColorsTheme)", boxShadow: "none", opacity: salvandoEncerrar ? 0.7 : 1 }}
                                >
                                    {salvandoEncerrar ? "Salvando..." : "Salvar no Prontuário"}
                                </button>
                            </div>
                        </div>
                    </div>
                )}
                {/* ------------------------------------ */}

                {/* ---- HEADER ---- */}
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: "0.5rem" }}>
                    <div>
                        <h1 style={{ margin: "0 0 0.5rem 0", color: "var(--PrimaryColorsTheme)", fontSize: "28px" }}>Painel do Especialista</h1>
                        <p className="text75">Bem-vindo(a) ao seu consultório virtual. Confira sua agenda de hoje.</p>
                    </div>
                </div>

                {/* ---- MÉTRICAS RÁPIDAS ---- */}
                <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: "1rem", marginBottom: "0.5rem" }}>
                    <div style={{ background: "var(--ThemeColor)", borderRadius: "var(--radius-lg)", border: "1px solid var(--LineColor)", padding: "1.5rem", boxShadow: "var(--shadow-sm)", display: "flex", alignItems: "center", gap: "1rem" }}>
                        <div style={{ width: "48px", height: "48px", borderRadius: "var(--radius-md)", background: "var(--PrimaryColorsBack)", color: "var(--PrimaryColorsTheme)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                            <CalendarDays size={22} strokeWidth={2} />
                        </div>
                        <div>
                            <p style={{ margin: "0 0 0.25rem 0", fontSize: "13px", fontWeight: 700, color: "var(--TextColor75)", textTransform: "uppercase", letterSpacing: "0.05em" }}>Consultas Hoje</p>
                            <p style={{ margin: 0, fontSize: "32px", fontWeight: 800, color: "var(--PrimaryColorsTheme)", fontFamily: "var(--font-secondary)" }}>
                                {metricas ? metricas.consultas_hoje ?? "—" : "—"}
                            </p>
                        </div>
                    </div>
                    <div style={{ background: "var(--ThemeColor)", borderRadius: "var(--radius-lg)", border: "1px solid var(--LineColor)", padding: "1.5rem", boxShadow: "var(--shadow-sm)", display: "flex", alignItems: "center", gap: "1rem" }}>
                        <div style={{ width: "48px", height: "48px", borderRadius: "var(--radius-md)", background: "var(--PrimaryColorsBack)", color: "var(--PrimaryColorsTheme)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                            <Users size={22} strokeWidth={2} />
                        </div>
                        <div>
                            <p style={{ margin: "0 0 0.25rem 0", fontSize: "13px", fontWeight: 700, color: "var(--TextColor75)", textTransform: "uppercase", letterSpacing: "0.05em" }}>Total de Pacientes</p>
                            <p style={{ margin: 0, fontSize: "32px", fontWeight: 800, color: "var(--PrimaryColorsTheme)", fontFamily: "var(--font-secondary)" }}>
                                {metricas ? metricas.total_pacientes ?? "—" : "—"}
                            </p>
                        </div>
                    </div>
                </div>

                {/* ---- CALENDARIO SEMANAL ---- */}
                <CalendarWeek
                    consultas={consultas}
                    semanaBase={semanaBase}
                    onMudarSemana={(dias) =>
                        setSemanaBase(prev => {
                            const d = new Date(prev);
                            d.setDate(d.getDate() + dias);
                            return d;
                        })
                    }
                />

                {/* ---- SELETOR DE SEMANA ---- */}
                <div className="camp-clinic camp-view" style={{ marginBottom: "0.5rem" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                        <h2 style={{ margin: 0 }}>Semana Atual</h2>
                        <span style={{ fontSize: "14px", color: "var(--TextColor75)", fontWeight: 600 }}>
                            {monday.toLocaleDateString("pt-BR", { month: "long", year: "numeric" })}
                        </span>
                    </div>

                    <div className="calendar-strip" style={{ marginBottom: 0, paddingBottom: "0.5rem" }}>
                        {weekDates.map(({ label, date }) => (
                            <div
                                key={label}
                                className={`calendar-day ${isSameDay(date, dataSelecionada) ? "active" : ""}`}
                                onClick={() => setDataSelecionada(new Date(date))}
                            >
                                <p>{label}</p>
                                <h3>{date.getDate()}</h3>
                            </div>
                        ))}
                    </div>
                </div>

                {/* ---- GRADE DE HORÁRIOS ---- */}
                <div className="camp-clinic" style={{ padding: "2.5rem" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.5rem" }}>
                        <h2 style={{ margin: 0 }}>Agenda de Hoje</h2>
                        <span style={{ background: "var(--PrimaryColorsBack)", color: "var(--PrimaryColorsTheme)", padding: "6px 14px", borderRadius: "999px", fontSize: "13px", fontWeight: 700, textTransform: "capitalize" }}>
                            {dataFormatada}
                        </span>
                    </div>

                    {loadingConsultas ? (
                        <div style={{ padding: "3rem", textAlign: "center", color: "var(--TextColor75)" }}>Carregando agenda...</div>
                    ) : (
                        <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                            {HORAS.map(hora => {
                                const consulta = consultaNoSlot(hora);
                                const badge = consulta ? (STATUS_BADGE[consulta.status] || STATUS_BADGE["Agendado"]) : null;
                                return (
                                    <div
                                        key={hora}
                                        style={{
                                            display: "grid",
                                            gridTemplateColumns: "80px 1fr",
                                            gap: "1rem",
                                            alignItems: "center",
                                            minHeight: "64px",
                                            borderRadius: "12px",
                                            padding: "0.5rem 0",
                                            borderBottom: "1px solid var(--LineColor)",
                                        }}
                                    >
                                        {/* horário */}
                                        <span style={{ fontFamily: "var(--font-secondary)", fontWeight: 600, fontSize: "15px", color: "var(--TextColor75)", textAlign: "right", paddingRight: "1rem" }}>
                                            {String(hora).padStart(2, "0")}:00
                                        </span>

                                        {/* slot */}
                                        {consulta ? (
                                            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", background: "var(--PrimaryColorsBack)", border: "1px solid var(--LineColor)", borderRadius: "var(--radius-md)", padding: "0.75rem 1.25rem" }}>
                                                <div>
                                                    <p style={{ margin: 0, fontWeight: 700, color: "var(--TextColor)", fontSize: "15px" }}>
                                                        {consulta.pacientes?.nome || consulta.paciente?.nome || "Paciente"}
                                                    </p>
                                                    <p style={{ margin: "2px 0 0 0", fontSize: "13px", color: "var(--TextColor75)" }}>
                                                        {consulta.tipo_atendimento || "Atendimento"}
                                                    </p>
                                                </div>
                                                <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
                                                    <span style={{ background: badge.bg, color: badge.color, padding: "4px 10px", borderRadius: "999px", fontSize: "12px", fontWeight: 700 }}>
                                                        {consulta.status || "Agendado"}
                                                    </span>
                                                    <button
                                                        onClick={() => abrirEncerrar(consulta)}
                                                        className="submit"
                                                        style={{ padding: "6px 14px", fontSize: "13px", borderRadius: "var(--radius-sm)", background: "var(--PrimaryColorsTheme)", boxShadow: "none" }}
                                                    >
                                                        Encerrar
                                                    </button>
                                                </div>
                                            </div>
                                        ) : (
                                            <div style={{ background: "var(--BackColor)", border: "1px dashed var(--LineColor)", borderRadius: "var(--radius-md)", padding: "0.75rem 1.25rem" }}>
                                                <p style={{ margin: 0, fontSize: "13px", color: "var(--TextColor75)", fontStyle: "italic" }}>Disponível</p>
                                            </div>
                                        )}
                                    </div>
                                );
                            })}
                        </div>
                    )}
                </div>
            </main>
        </>
    );
}

export default SpecialistDashboard;

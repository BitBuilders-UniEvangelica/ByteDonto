import { useState, useEffect } from "react";
import { Plus, X } from "lucide-react";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

const STATUS_BADGE = {
    "Agendado":   { bg: "var(--PrimaryColorsBack)", color: "var(--PrimaryColorsTheme)", label: "Agendado" },
    "Finalizado": { bg: "var(--SuccessBack)", color: "var(--SuccessText)", label: "Finalizado" },
    "Cancelado":  { bg: "var(--DangerBack)", color: "var(--DangerText)", label: "Cancelado" },
    "Faltou":     { bg: "var(--BackColor)", color: "var(--TextColor75)", label: "Faltou" },
};

const TIPOS_ATENDIMENTO = ["Avaliação", "Retorno", "Procedimento", "Emergência", "Manutenção"];

function formatarData(dataString) {
    if (!dataString) return "";
    try {
        const d = new Date(dataString);
        return d.toLocaleDateString("pt-BR", {
            day: "2-digit",
            month: "long",
            year: "numeric",
        });
    } catch {
        return dataString;
    }
}

function formatarHora(dataString) {
    if (!dataString) return "";
    try {
        const d = new Date(dataString);
        return d.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
    } catch {
        return "";
    }
}

function BadgeStatus({ status }) {
    const config = STATUS_BADGE[status] || { bg: "var(--BackColor)", color: "var(--TextColor75)", label: status || "—" };
    return (
        <span style={{
            background: config.bg,
            color: config.color,
            padding: "3px 10px",
            borderRadius: "999px",
            fontSize: "12px",
            fontWeight: 700,
            whiteSpace: "nowrap",
        }}>
            {config.label}
        </span>
    );
}

function CardConsulta({ consulta, onEvolucaoChange }) {
    const [evolucao, setEvolucao] = useState(consulta.evolucao_clinica || "");
    const [editando, setEditando] = useState(false);

    return (
        <div style={{
            background: "var(--ThemeColor)",
            border: "1px solid var(--LineColor)",
            borderRadius: "var(--radius-md)",
            padding: "1.25rem",
            display: "flex",
            flexDirection: "column",
            gap: "0.75rem",
            position: "relative",
            boxShadow: "var(--shadow-sm)",
        }}>
            {/* Linha de tempo */}
            <div style={{ position: "absolute", left: "-19px", top: "20px", width: "10px", height: "10px", borderRadius: "50%", background: "var(--PrimaryColorsTheme)", border: "2px solid var(--ThemeColor)", outline: "2px solid var(--PrimaryColorsTheme)" }} />

            {/* Cabeçalho */}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "0.5rem", flexWrap: "wrap" }}>
                <div>
                    <span style={{ fontSize: "13px", color: "var(--TextColor75)" }}>
                        {formatarData(consulta.data_agendada)}
                        {formatarHora(consulta.data_agendada) ? ` às ${formatarHora(consulta.data_agendada)}` : ""}
                    </span>
                    <h4 style={{ margin: "2px 0 0 0", fontSize: "16px", color: "var(--TextColor)", fontWeight: 700 }}>
                        {consulta.tipo_atendimento || "Atendimento"}
                    </h4>
                    {consulta.dentista?.nome && (
                        <span style={{ fontSize: "12px", color: "var(--TextColor75)" }}>
                            Dr(a). {consulta.dentista.nome}
                        </span>
                    )}
                </div>
                <BadgeStatus status={consulta.status} />
            </div>

            {/* Procedimentos */}
            {consulta.procedimentos_descritos && (
                <div>
                    <p style={{ margin: "0 0 4px 0", fontSize: "12px", fontWeight: 700, color: "var(--TextColor75)", textTransform: "uppercase", letterSpacing: "0.4px" }}>
                        Procedimentos
                    </p>
                    <p style={{ margin: 0, fontSize: "14px", color: "var(--TextColor)" }}>
                        {consulta.procedimentos_descritos}
                    </p>
                </div>
            )}

            {/* Evolução clínica — editável inline */}
            <div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
                    <p style={{ margin: 0, fontSize: "12px", fontWeight: 700, color: "var(--TextColor75)", textTransform: "uppercase", letterSpacing: "0.4px" }}>
                        Evolução Clínica
                    </p>
                    {!editando && (
                        <button
                            onClick={() => setEditando(true)}
                            style={{ background: "none", border: "none", cursor: "pointer", fontSize: "12px", color: "var(--PrimaryColorsTheme)", fontWeight: 600, padding: 0 }}
                        >
                            Editar
                        </button>
                    )}
                </div>
                {editando ? (
                    <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                        <textarea
                            value={evolucao}
                            onChange={e => setEvolucao(e.target.value)}
                            rows={3}
                            placeholder="Descrição da evolução clínica..."
                            style={{
                                width: "100%",
                                padding: "8px 10px",
                                borderRadius: "var(--radius-sm)",
                                border: "1px solid var(--LineColor)",
                                fontSize: "14px",
                                resize: "vertical",
                                fontFamily: "inherit",
                                boxSizing: "border-box",
                            }}
                        />
                        <div style={{ display: "flex", gap: "8px" }}>
                            <button
                                onClick={() => { onEvolucaoChange(consulta.id, evolucao); setEditando(false); }}
                                style={{ padding: "6px 14px", background: "var(--PrimaryColorsTheme)", color: "white", border: "none", borderRadius: "var(--radius-sm)", fontSize: "13px", fontWeight: 700, cursor: "pointer" }}
                            >
                                Salvar
                            </button>
                            <button
                                onClick={() => { setEvolucao(consulta.evolucao_clinica || ""); setEditando(false); }}
                                style={{ padding: "6px 14px", background: "transparent", color: "var(--TextColor75)", border: "1px solid var(--LineColor)", borderRadius: "var(--radius-sm)", fontSize: "13px", cursor: "pointer" }}
                            >
                                Cancelar
                            </button>
                        </div>
                    </div>
                ) : (
                    <p style={{ margin: 0, fontSize: "14px", color: evolucao ? "var(--TextColor)" : "var(--TextColor75)", fontStyle: evolucao ? "normal" : "italic" }}>
                        {evolucao || "Nenhuma evolução registrada."}
                    </p>
                )}
            </div>
        </div>
    );
}

const hoje = new Date().toISOString().split("T")[0];
const horaAtual = new Date().toTimeString().slice(0, 5);

const FORM_INICIAL = {
    data: hoje,
    hora: horaAtual,
    tipo_atendimento: "Avaliação",
    procedimentos_descritos: "",
    evolucao_clinica: "",
    status: "Agendado",
};

export default function RegistroClinico({ pacienteId, token }) {
    const [consultas, setConsultas] = useState([]);
    const [loading, setLoading] = useState(true);
    const [erro, setErro] = useState(null);
    const [mostrarForm, setMostrarForm] = useState(false);
    const [form, setForm] = useState(FORM_INICIAL);
    const [salvando, setSalvando] = useState(false);
    const [erroForm, setErroForm] = useState(null);

    useEffect(() => {
        if (!pacienteId) { setLoading(false); return; }
        setLoading(true);
        setErro(null);

        fetch(`${API_URL}/api/consultas/?paciente_id=${pacienteId}`, {
            headers: { Authorization: `Bearer ${token}` },
        })
            .then(res => res.json().then(data => ({ ok: res.ok, data })))
            .then(({ ok, data }) => {
                if (!ok) throw new Error(data.error || "Erro ao buscar consultas");
                // Ordena da mais recente para a mais antiga
                const ordenadas = [...(Array.isArray(data) ? data : [])].sort((a, b) => {
                    return new Date(b.data_agendada) - new Date(a.data_agendada);
                });
                setConsultas(ordenadas);
            })
            .catch(err => setErro(err.message))
            .finally(() => setLoading(false));
    }, [pacienteId, token]);

    function handleEvolucaoChange(consultaId, novaEvolucao) {
        setConsultas(prev =>
            prev.map(c => c.id === consultaId ? { ...c, evolucao_clinica: novaEvolucao } : c)
        );
        // Persiste no backend silenciosamente
        fetch(`${API_URL}/api/consultas/${consultaId}`, {
            method: "PUT",
            headers: {
                "Content-Type": "application/json",
                Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify({ evolucao_clinica: novaEvolucao }),
        }).catch(err => console.warn("Erro ao salvar evolucao:", err));
    }

    async function handleSubmitForm(e) {
        e.preventDefault();
        setSalvando(true);
        setErroForm(null);

        const dataAgendada = form.hora ? `${form.data}T${form.hora}:00` : `${form.data}T00:00:00`;

        const body = {
            paciente_id: pacienteId,
            data_agendada: dataAgendada,
            tipo_atendimento: form.tipo_atendimento,
            procedimentos_descritos: form.procedimentos_descritos,
            evolucao_clinica: form.evolucao_clinica,
            status: form.status,
        };

        try {
            const res = await fetch(`${API_URL}/api/consultas/`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${token}`,
                },
                body: JSON.stringify(body),
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || "Erro ao salvar registro");

            // Adiciona no topo (mais recente)
            setConsultas(prev => [data, ...prev]);
            setForm(FORM_INICIAL);
            setMostrarForm(false);
        } catch (err) {
            setErroForm(err.message);
        } finally {
            setSalvando(false);
        }
    }

    return (
        <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
            {/* Botao de adicionar */}
            <div style={{ display: "flex", justifyContent: "flex-end" }}>
                <button
                    onClick={() => { setMostrarForm(v => !v); setErroForm(null); }}
                    style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "6px",
                        padding: "10px 20px",
                        background: mostrarForm ? "transparent" : "var(--PrimaryColorsTheme)",
                        color: mostrarForm ? "var(--TextColor75)" : "white",
                        border: mostrarForm ? "1px solid var(--LineColor)" : "none",
                        borderRadius: "var(--radius-md)",
                        fontWeight: 700,
                        fontSize: "14px",
                        cursor: "pointer",
                    }}
                >
                    {mostrarForm ? <><X size={16} strokeWidth={2.5} /> Cancelar</> : <><Plus size={16} strokeWidth={2.5} /> Adicionar Registro Clínico</>}
                </button>
            </div>

            {/* Formulário inline */}
            {mostrarForm && (
                <form
                    onSubmit={handleSubmitForm}
                    style={{
                        background: "var(--ThemeColor)",
                        border: "1px solid var(--LineColor)",
                        borderRadius: "var(--radius-lg)",
                        padding: "1.5rem",
                        display: "flex",
                        flexDirection: "column",
                        gap: "1rem",
                        animation: "fadeIn 0.25s",
                    }}
                >
                    <h4 style={{ margin: 0, color: "var(--PrimaryColorsTheme)", fontSize: "16px" }}>
                        Novo Registro Clínico
                    </h4>

                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "1rem" }}>
                        <div>
                            <p style={{ margin: "0 0 6px 0", fontSize: "13px", fontWeight: 700, color: "var(--TextColor75)" }}>Data</p>
                            <input
                                type="date"
                                value={form.data}
                                onChange={e => setForm(p => ({ ...p, data: e.target.value }))}
                                required
                                style={{ width: "100%", padding: "8px 10px", borderRadius: "var(--radius-sm)", border: "1px solid var(--LineColor)", fontSize: "14px", boxSizing: "border-box" }}
                            />
                        </div>
                        <div>
                            <p style={{ margin: "0 0 6px 0", fontSize: "13px", fontWeight: 700, color: "var(--TextColor75)" }}>Hora</p>
                            <input
                                type="time"
                                value={form.hora}
                                onChange={e => setForm(p => ({ ...p, hora: e.target.value }))}
                                style={{ width: "100%", padding: "8px 10px", borderRadius: "var(--radius-sm)", border: "1px solid var(--LineColor)", fontSize: "14px", boxSizing: "border-box" }}
                            />
                        </div>
                        <div>
                            <p style={{ margin: "0 0 6px 0", fontSize: "13px", fontWeight: 700, color: "var(--TextColor75)" }}>Status</p>
                            <select
                                value={form.status}
                                onChange={e => setForm(p => ({ ...p, status: e.target.value }))}
                                style={{ width: "100%", padding: "8px 10px", borderRadius: "var(--radius-sm)", border: "1px solid var(--LineColor)", fontSize: "14px", background: "var(--ThemeColor)", boxSizing: "border-box" }}
                            >
                                {Object.keys(STATUS_BADGE).map(s => <option key={s} value={s}>{s}</option>)}
                            </select>
                        </div>
                    </div>

                    <div>
                        <p style={{ margin: "0 0 6px 0", fontSize: "13px", fontWeight: 700, color: "var(--TextColor75)" }}>Tipo de Atendimento</p>
                        <select
                            value={form.tipo_atendimento}
                            onChange={e => setForm(p => ({ ...p, tipo_atendimento: e.target.value }))}
                            style={{ width: "100%", padding: "8px 10px", borderRadius: "var(--radius-sm)", border: "1px solid var(--LineColor)", fontSize: "14px", background: "var(--ThemeColor)", boxSizing: "border-box" }}
                        >
                            {TIPOS_ATENDIMENTO.map(t => <option key={t} value={t}>{t}</option>)}
                        </select>
                    </div>

                    <div>
                        <p style={{ margin: "0 0 6px 0", fontSize: "13px", fontWeight: 700, color: "var(--TextColor75)" }}>Procedimentos Realizados</p>
                        <textarea
                            value={form.procedimentos_descritos}
                            onChange={e => setForm(p => ({ ...p, procedimentos_descritos: e.target.value }))}
                            rows={2}
                            placeholder="Descreva os procedimentos realizados..."
                            style={{ width: "100%", padding: "8px 10px", borderRadius: "var(--radius-sm)", border: "1px solid var(--LineColor)", fontSize: "14px", resize: "vertical", fontFamily: "inherit", boxSizing: "border-box" }}
                        />
                    </div>

                    <div>
                        <p style={{ margin: "0 0 6px 0", fontSize: "13px", fontWeight: 700, color: "var(--TextColor75)" }}>Evolução Clínica / Observações</p>
                        <textarea
                            value={form.evolucao_clinica}
                            onChange={e => setForm(p => ({ ...p, evolucao_clinica: e.target.value }))}
                            rows={3}
                            placeholder="Evolução clínica, resposta ao tratamento, observações..."
                            style={{ width: "100%", padding: "8px 10px", borderRadius: "var(--radius-sm)", border: "1px solid var(--LineColor)", fontSize: "14px", resize: "vertical", fontFamily: "inherit", boxSizing: "border-box" }}
                        />
                    </div>

                    {erroForm && (
                        <div style={{ background: "var(--DangerBack)", border: "1px solid var(--LineColor)", borderRadius: "var(--radius-sm)", padding: "10px 14px", color: "var(--DangerText)", fontSize: "14px" }}>
                            {erroForm}
                        </div>
                    )}

                    <div style={{ display: "flex", gap: "0.75rem" }}>
                        <button
                            type="submit"
                            disabled={salvando}
                            style={{
                                padding: "10px 24px",
                                background: "var(--PrimaryColorsTheme)", opacity: salvando ? 0.7 : 1,
                                color: "white",
                                border: "none",
                                borderRadius: "var(--radius-sm)",
                                fontWeight: 700,
                                fontSize: "14px",
                                cursor: salvando ? "not-allowed" : "pointer",
                            }}
                        >
                            {salvando ? "Salvando..." : "Salvar Registro"}
                        </button>
                        <button
                            type="button"
                            onClick={() => { setMostrarForm(false); setForm(FORM_INICIAL); setErroForm(null); }}
                            style={{ padding: "10px 16px", background: "transparent", color: "var(--TextColor75)", border: "1px solid var(--LineColor)", borderRadius: "var(--radius-sm)", fontWeight: 600, fontSize: "14px", cursor: "pointer" }}
                        >
                            Cancelar
                        </button>
                    </div>
                </form>
            )}

            {/* Timeline */}
            {loading && (
                <p style={{ color: "var(--TextColor75)", fontSize: "14px" }}>Carregando histórico...</p>
            )}

            {erro && !loading && (
                <div style={{ background: "var(--DangerBack)", border: "1px solid var(--LineColor)", borderRadius: "var(--radius-md)", padding: "1rem", color: "var(--DangerText)", fontSize: "14px" }}>
                    Erro ao carregar registros: {erro}
                </div>
            )}

            {!loading && !erro && consultas.length === 0 && (
                <p style={{ color: "var(--TextColor75)", fontSize: "14px", fontStyle: "italic" }}>
                    Nenhum registro clínico encontrado para este paciente.
                </p>
            )}

            {!loading && !erro && consultas.length > 0 && (
                <div style={{ position: "relative", paddingLeft: "28px", display: "flex", flexDirection: "column", gap: "1.25rem" }}>
                    {/* Linha vertical da timeline */}
                    <div style={{ position: "absolute", left: "15px", top: "20px", bottom: "20px", width: "2px", background: "var(--LineColor)", borderRadius: "1px" }} />

                    {consultas.map(consulta => (
                        <CardConsulta
                            key={consulta.id || Math.random()}
                            consulta={consulta}
                            onEvolucaoChange={handleEvolucaoChange}
                        />
                    ))}
                </div>
            )}
        </div>
    );
}

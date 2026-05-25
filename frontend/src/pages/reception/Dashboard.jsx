/* IMPORTS */
import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { apiGetPacientes, apiGetEquipe, apiCriarConsulta, apiGetConsultas, apiAtualizarConsulta } from "../../services/api";
import Section from "../../components/section/SectionAuth";
import SideBar from "../../components/bar/SideBar";
import Card from "../../components/card/CardInfo";
import { formatCPF } from "../../utils/formatters";
import { useReceptionSidebar } from "../../hooks/useSidebar";
import { X, Check, Plus, Search, CalendarDays, UserCheck, Clock, UserX, Users } from "lucide-react";

const FORM_INICIAL = {
    paciente_id: "",
    dentista_id: "",
    tipo: "",
    data: "",
    hora: "",
    motivo: "",
};

/* Tokens de cor por status da consulta */
const STATUS_TOKENS = {
    "Agendado": { back: "var(--WarningBack)", text: "var(--WarningText)" },
    "Aguardando": { back: "var(--PrimaryColorsBack)", text: "var(--PrimaryColorsTheme)" },
    "Finalizado": { back: "var(--SuccessBack)", text: "var(--SuccessText)" },
    "Cancelado": { back: "var(--DangerBack)", text: "var(--DangerText)" },
    "Faltou": { back: "var(--BackColor)", text: "var(--TextColor75)" },
};

function StatusPill({ status }) {
    const tk = STATUS_TOKENS[status] || { back: "var(--BackColor)", text: "var(--TextColor75)" };
    return (
        <span style={{ background: tk.back, color: tk.text, padding: '3px 12px', borderRadius: '999px', fontSize: '12px', fontWeight: 700, whiteSpace: 'nowrap' }}>
            {status || "—"}
        </span>
    );
}

/* MAIN COMPONENT */
function ReceptionDashboard() {
    const { token } = useAuth();

    const [pacientes, setPacientes] = useState([]);
    const [especialistas, setEspecialistas] = useState([]);
    const [consultas, setConsultas] = useState([]);

    // Agendamento modal
    const [showAgendamento, setShowAgendamento] = useState(false);
    const [agForm, setAgForm] = useState(FORM_INICIAL);
    const [agEnviando, setAgEnviando] = useState(false);
    const [agErro, setAgErro] = useState(null);
    const [agSucesso, setAgSucesso] = useState(false);

    // Autocomplete no modal
    const [searchName, setSearchName] = useState("");
    const [selectedPatient, setSelectedPatient] = useState(null);

    // Busca rápida
    const [quickSearch, setQuickSearch] = useState("");

    // Ações de status na agenda
    const [statusErro, setStatusErro] = useState(null);
    const [atualizandoId, setAtualizandoId] = useState(null);

    const opc_bar = useReceptionSidebar("dashboard");

    useEffect(() => {
        Promise.all([
            apiGetPacientes(token).catch(() => []),
            apiGetEquipe(token).catch(() => []),
            apiGetConsultas(token).catch(() => []),
        ]).then(([p, e, c]) => {
            setPacientes(p);
            setEspecialistas(e.filter(m => m.papel === "Especialista"));
            setConsultas(c);
        });
    }, [token]);

    async function recarregarConsultas() {
        try {
            const c = await apiGetConsultas(token);
            setConsultas(c);
        } catch {
            /* mantém a lista atual se a recarga falhar */
        }
    }

    async function alterarStatus(id, novoStatus) {
        setStatusErro(null);
        setAtualizandoId(id);
        try {
            await apiAtualizarConsulta(token, id, { status: novoStatus });
            await recarregarConsultas();
        } catch {
            setStatusErro("Não foi possível atualizar o status da consulta. Tente novamente em instantes ou contate o suporte.");
        } finally {
            setAtualizandoId(null);
        }
    }

    // Derivados de autocomplete
    const filteredPatients = searchName.length > 1 && !selectedPatient
        ? pacientes.filter(p =>
            p.nome?.toLowerCase().includes(searchName.toLowerCase()) ||
            p.cpf?.includes(searchName) ||
            p.telefone_whatsapp?.includes(searchName)
        )
        : [];

    const filteredQuick = quickSearch.length > 1
        ? pacientes.filter(p =>
            p.nome?.toLowerCase().includes(quickSearch.toLowerCase()) ||
            p.cpf?.includes(quickSearch) ||
            p.telefone_whatsapp?.includes(quickSearch)
        )
        : [];

    function abrirModal() {
        setAgForm(FORM_INICIAL);
        setSearchName("");
        setSelectedPatient(null);
        setAgErro(null);
        setAgSucesso(false);
        setShowAgendamento(true);
    }

    async function handleAgendar(e) {
        e.preventDefault();
        if (!selectedPatient) {
            setAgErro("Selecione um paciente cadastrado.");
            return;
        }
        setAgEnviando(true);
        setAgErro(null);
        try {
            const data_agendada = `${agForm.data}T${agForm.hora}:00`;
            const nova = await apiCriarConsulta(token, {
                paciente_id: selectedPatient.id,
                dentista_id: agForm.dentista_id || null,
                tipo_atendimento: agForm.tipo,
                data_agendada,
                procedimentos_descritos: agForm.motivo,
            });
            setConsultas(prev => [nova, ...prev]);
            setAgSucesso(true);
            setTimeout(() => setShowAgendamento(false), 1500);
        } catch (err) {
            setAgErro(err.message);
        } finally {
            setAgEnviando(false);
        }
    }

    const hoje = new Date().toISOString().slice(0, 10);
    const consultasHoje = consultas
        .filter(c => c.data_agendada?.startsWith(hoje))
        .sort((a, b) => (a.data_agendada || "").localeCompare(b.data_agendada || ""));
    const salaDeEspera = consultasHoje.filter(c => c.status === "Aguardando");

    return (
        <>
            <Section type_styles="reception" />
            <SideBar opc={opc_bar} styles="reception" />

            <main className="mainBar reception" style={{ position: 'relative' }}>

                {/* ---------- MODAL DE AGENDAMENTO ---------- */}
                {showAgendamento && (
                    <div style={{ position: 'fixed', top: 0, left: 0, width: '100vw', height: '100vh', background: 'rgba(15, 23, 42, 0.4)', backdropFilter: 'blur(8px)', zIndex: 9999, display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
                        <div style={{ background: 'white', padding: '2.5rem', borderRadius: '16px', width: '100%', maxWidth: '750px', boxShadow: 'var(--shadow-sm)', animation: 'fadeIn 0.2s', border: '1px solid var(--LineColor)' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '2rem' }}>
                                <div>
                                    <span style={{ background: 'var(--PrimaryColorsBack)', color: 'var(--PrimaryColorsTheme)', padding: '6px 12px', borderRadius: '999px', fontSize: '12px', fontWeight: 700, marginBottom: '12px', display: 'inline-block', letterSpacing: '0.04em' }}>NOVO EVENTO</span>
                                    <h2 style={{ color: 'var(--TextColor)', margin: 0, fontSize: '26px' }}>Agendar Consulta</h2>
                                    <p style={{ color: 'var(--TextColor75)', margin: '6px 0 0 0' }}>Selecione paciente, profissional e horário.</p>
                                </div>
                                <button aria-label="Fechar" onClick={() => setShowAgendamento(false)} style={{ background: 'var(--BackColor)', border: '1px solid var(--LineColor)', width: '40px', height: '40px', borderRadius: '10px', cursor: 'pointer', color: 'var(--TextColor)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}><X size={18} strokeWidth={2} /></button>
                            </div>

                            {agSucesso ? (
                                <div style={{ textAlign: 'center', padding: '2rem 0' }}>
                                    <div style={{ width: '64px', height: '64px', borderRadius: '50%', background: 'var(--SuccessBack)', color: 'var(--SuccessText)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 1rem' }}>
                                        <Check size={32} strokeWidth={2.5} />
                                    </div>
                                    <p style={{ fontWeight: 700, color: 'var(--SuccessText)', fontSize: '18px' }}>Consulta agendada com sucesso!</p>
                                </div>
                            ) : (
                                <form onSubmit={handleAgendar} className="forms-section" style={{ padding: 0 }}>
                                    {agErro && (
                                        <div style={{ background: 'var(--DangerBack)', color: 'var(--DangerText)', padding: '10px 14px', borderRadius: '8px', marginBottom: '1rem', fontSize: '14px' }}>
                                            {agErro}
                                        </div>
                                    )}

                                    <div className="field" style={{ marginBottom: '1rem', position: 'relative' }}>
                                        <label>Buscar Paciente Cadastrado *</label>
                                        <input
                                            type="text"
                                            placeholder="Digite Nome, CPF ou Telefone..."
                                            style={{ width: '100%' }}
                                            value={selectedPatient ? selectedPatient.nome : searchName}
                                            onChange={e => { setSearchName(e.target.value); setSelectedPatient(null); }}
                                        />
                                        {filteredPatients.length > 0 && (
                                            <ul style={{ position: 'absolute', top: '100%', left: 0, width: '100%', background: 'white', border: '1px solid var(--LineColor)', borderRadius: '12px', listStyle: 'none', padding: '0.5rem', margin: '4px 0 0 0', boxShadow: '0 10px 25px rgba(0,0,0,0.15)', zIndex: 10, maxHeight: '200px', overflowY: 'auto' }}>
                                                {filteredPatients.map(p => (
                                                    <li key={p.id} onClick={() => { setSelectedPatient(p); setSearchName(""); }}
                                                        style={{ padding: '12px', borderRadius: '8px', cursor: 'pointer', borderBottom: '1px solid var(--LineColor)' }}>
                                                        <p style={{ fontWeight: 700, margin: 0, color: 'var(--PrimaryColorsTheme)' }}>{p.nome}</p>
                                                        <span style={{ fontSize: '12px', color: 'var(--TextColor75)' }}>CPF: {formatCPF(p.cpf)}</span>
                                                    </li>
                                                ))}
                                            </ul>
                                        )}
                                        <Link to="/reception/patient/register" style={{ color: 'var(--PrimaryColorsTheme)', fontSize: '13px', marginTop: '12px', display: 'inline-flex', alignItems: 'center', gap: '4px', fontWeight: 700 }}>
                                            <Plus size={14} strokeWidth={2.5} /> Paciente não encontrado? (Cadastrar)
                                        </Link>
                                    </div>

                                    <div className="flex-inpus">
                                        <div className="field">
                                            <label>Especialista Alocado</label>
                                            <select style={{ width: '100%' }} value={agForm.dentista_id}
                                                onChange={e => setAgForm(p => ({ ...p, dentista_id: e.target.value }))}>
                                                <option value="">Selecione...</option>
                                                {especialistas.map(e => (
                                                    <option key={e.id} value={e.id}>{e.nome}</option>
                                                ))}
                                            </select>
                                        </div>
                                        <div className="field">
                                            <label>Tipo de Atendimento</label>
                                            <select style={{ width: '100%' }} value={agForm.tipo}
                                                onChange={e => setAgForm(p => ({ ...p, tipo: e.target.value }))}>
                                                <option value="">Selecione...</option>
                                                <option value="Primeira Avaliação">Primeira Avaliação</option>
                                                <option value="Retorno">Retorno</option>
                                                <option value="Procedimento">Procedimento/Cirurgia</option>
                                            </select>
                                        </div>
                                    </div>

                                    <div className="flex-inpus">
                                        <div className="field">
                                            <label>Data *</label>
                                            <input type="date" required style={{ width: '100%' }} value={agForm.data}
                                                onChange={e => setAgForm(p => ({ ...p, data: e.target.value }))} />
                                        </div>
                                        <div className="field">
                                            <label>Horário *</label>
                                            <input type="time" required style={{ width: '100%' }} value={agForm.hora}
                                                onChange={e => setAgForm(p => ({ ...p, hora: e.target.value }))} />
                                        </div>
                                    </div>

                                    <div className="field" style={{ marginBottom: '0' }}>
                                        <label>Motivo da Consulta</label>
                                        <input type="text" placeholder="Ex: Avaliação de dor, manutenção do aparelho..." style={{ width: '100%' }}
                                            value={agForm.motivo} onChange={e => setAgForm(p => ({ ...p, motivo: e.target.value }))} />
                                    </div>

                                    <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '1rem', borderTop: '1px solid var(--LineColor)', paddingTop: '1.5rem', marginTop: '2rem' }}>
                                        <button type="button" onClick={() => setShowAgendamento(false)} className="submit"
                                            style={{ padding: '14px 24px', background: 'var(--BackColor)', color: 'var(--TextColor)', border: '1px solid var(--LineColor)', boxShadow: 'none' }}
                                            disabled={agEnviando}>Cancelar</button>
                                        <button type="submit" className="submit" style={{ padding: '14px 36px', background: 'var(--PrimaryColorsTheme)', boxShadow: 'none' }}
                                            disabled={agEnviando}>{agEnviando ? "Agendando..." : "Confirmar na Agenda"}</button>
                                    </div>
                                </form>
                            )}
                        </div>
                    </div>
                )}
                {/* ------------------------------------------------ */}

                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: "2rem" }}>
                    <div>
                        <h1 style={{ margin: '0 0 0.5rem 0', color: 'var(--PrimaryColorsTheme)', fontSize: '28px' }}>Atendimento e Recepção</h1>
                        <p className="text75">Gerencie os agendamentos e controle os pacientes na sala de espera.</p>
                    </div>
                    <button onClick={abrirModal} style={{ background: 'var(--PrimaryColorsTheme)', color: 'white', padding: '12px 24px', borderRadius: '12px', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '0.5rem', boxShadow: 'var(--shadow-sm)', border: 'none', cursor: 'pointer' }}>
                        <Plus size={18} strokeWidth={2.5} /> Agendar Nova Consulta
                    </button>
                </div>

                {/* BUSCA RÁPIDA */}
                <div className="camp-clinic camp-register" style={{ marginBottom: "2rem", padding: "1.5rem 2.5rem" }}>
                    <div style={{ display: 'flex', gap: '1rem', alignItems: 'flex-end' }}>
                        <div className="field" style={{ flex: 1, margin: 0, position: 'relative' }}>
                            <label style={{ color: 'var(--PrimaryColorsTheme)' }}>Busca Rápida de Paciente</label>
                            <input type="text" placeholder="Digite o nome, CPF ou Telefone..." style={{ margin: 0, width: '100%', maxWidth: 'none' }}
                                value={quickSearch} onChange={e => setQuickSearch(e.target.value)} />
                            <Search size={16} strokeWidth={2} style={{ position: 'absolute', right: '14px', bottom: '14px', color: 'var(--TextColor75)', pointerEvents: 'none' }} />
                            {filteredQuick.length > 0 && (
                                <ul style={{ position: 'absolute', top: '100%', left: 0, width: '100%', background: 'white', border: '1px solid var(--LineColor)', borderRadius: '12px', listStyle: 'none', padding: '0.5rem', margin: '4px 0 0 0', boxShadow: '0 10px 25px rgba(0,0,0,0.15)', zIndex: 10 }}>
                                    {filteredQuick.map(p => (
                                        <li key={p.id} onClick={() => setQuickSearch(p.nome)}
                                            style={{ padding: '12px', borderRadius: '8px', cursor: 'pointer', borderBottom: '1px solid var(--LineColor)' }}>
                                            <p style={{ fontWeight: 700, margin: 0, color: 'var(--PrimaryColorsTheme)' }}>{p.nome}</p>
                                            <span style={{ fontSize: '12px', color: 'var(--TextColor75)' }}>CPF: {formatCPF(p.cpf)}</span>
                                        </li>
                                    ))}
                                </ul>
                            )}
                        </div>
                        <Link to="/reception/patients" className="submit" style={{ padding: '16px 32px', textAlign: 'center' }}>Acessar Ficha</Link>
                    </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '2rem' }}>
                    {/* AGENDA GERAL */}
                    <div className="camp-clinic" style={{ padding: '2.5rem' }}>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.5rem" }}>
                            <div style={{ display: "flex", alignItems: "center", gap: '0.6rem' }}>
                                <CalendarDays size={20} strokeWidth={2} style={{ color: 'var(--PrimaryColorsTheme)' }} />
                                <h2 style={{ margin: 0 }}>Agenda de Hoje</h2>
                            </div>
                            <span style={{ background: 'var(--PrimaryColorsBack)', color: 'var(--PrimaryColorsTheme)', padding: '2px 10px', borderRadius: '999px', fontWeight: 700, fontSize: '13px' }}>{consultasHoje.length}</span>
                        </div>

                        {statusErro && (
                            <div style={{ background: 'var(--DangerBack)', color: 'var(--DangerText)', padding: '10px 14px', borderRadius: '8px', marginBottom: '1rem', fontSize: '13px' }}>
                                {statusErro}
                            </div>
                        )}

                        {consultasHoje.length === 0 ? (
                            <p className="text75" style={{ textAlign: 'center', padding: '2rem' }}>Nenhum agendamento para hoje.</p>
                        ) : (
                            <div className="table">
                                <div className="table-header" style={{ gridTemplateColumns: '0.8fr 1.4fr 1.2fr 1fr 0.9fr 1.6fr' }}>
                                    <p className="text75">Horário</p>
                                    <p className="text75">Paciente</p>
                                    <p className="text75">Especialista</p>
                                    <p className="text75">Tipo</p>
                                    <p className="text75">Status</p>
                                    <p className="text75">Ações</p>
                                </div>
                                <div className="table-body">
                                    {consultasHoje.map(c => {
                                        const podeCheckin = c.status === "Agendado";
                                        const podeFaltou = c.status === "Agendado";
                                        const podeCancelar = c.status === "Agendado" || c.status === "Aguardando";
                                        const ocupado = atualizandoId === c.id;
                                        const temAcoes = podeCheckin || podeFaltou || podeCancelar;
                                        return (
                                            <div key={c.id} className="table-row" style={{ gridTemplateColumns: '0.8fr 1.4fr 1.2fr 1fr 0.9fr 1.6fr', alignItems: 'center' }}>
                                                <p style={{ fontWeight: 600 }}>{c.data_agendada?.slice(11, 16) || "—"}</p>
                                                <p style={{ fontWeight: 500 }}>{c.pacientes?.nome || "—"}</p>
                                                <p className="text75">{c.dentista?.nome || "—"}</p>
                                                <p className="text75">{c.tipo_atendimento || "—"}</p>
                                                <p><StatusPill status={c.status} /></p>
                                                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                                                    {temAcoes ? (
                                                        <>
                                                            {podeCheckin && (
                                                                <button onClick={() => alterarStatus(c.id, "Aguardando")} disabled={ocupado} title="Check-in"
                                                                    style={{ display: 'flex', alignItems: 'center', gap: '4px', background: 'var(--PrimaryColorsBack)', color: 'var(--PrimaryColorsTheme)', border: '1px solid var(--LineColor)', borderRadius: '8px', padding: '5px 10px', fontSize: '12px', fontWeight: 700, cursor: ocupado ? 'default' : 'pointer', opacity: ocupado ? 0.6 : 1 }}>
                                                                    <UserCheck size={14} strokeWidth={2.2} /> Check-in
                                                                </button>
                                                            )}
                                                            {podeFaltou && (
                                                                <button onClick={() => alterarStatus(c.id, "Faltou")} disabled={ocupado} title="Marcar falta"
                                                                    style={{ display: 'flex', alignItems: 'center', gap: '4px', background: 'var(--BackColor)', color: 'var(--TextColor75)', border: '1px solid var(--LineColor)', borderRadius: '8px', padding: '5px 10px', fontSize: '12px', fontWeight: 700, cursor: ocupado ? 'default' : 'pointer', opacity: ocupado ? 0.6 : 1 }}>
                                                                    <UserX size={14} strokeWidth={2.2} /> Faltou
                                                                </button>
                                                            )}
                                                            {podeCancelar && (
                                                                <button onClick={() => alterarStatus(c.id, "Cancelado")} disabled={ocupado} title="Cancelar consulta"
                                                                    style={{ display: 'flex', alignItems: 'center', gap: '4px', background: 'var(--DangerBack)', color: 'var(--DangerText)', border: '1px solid var(--LineColor)', borderRadius: '8px', padding: '5px 10px', fontSize: '12px', fontWeight: 700, cursor: ocupado ? 'default' : 'pointer', opacity: ocupado ? 0.6 : 1 }}>
                                                                    <X size={14} strokeWidth={2.2} /> Cancelar
                                                                </button>
                                                            )}
                                                        </>
                                                    ) : (
                                                        <span className="text75" style={{ fontSize: '12px' }}>—</span>
                                                    )}
                                                </div>
                                            </div>
                                        );
                                    })}
                                </div>
                            </div>
                        )}
                    </div>

                    {/* SALA DE ESPERA */}
                    <div className="camp-clinic" style={{ padding: '2.5rem' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                                <Users size={20} strokeWidth={2} style={{ color: 'var(--PrimaryColorsTheme)' }} />
                                <h2 style={{ margin: '0', color: 'var(--PrimaryColorsTheme)' }}>Sala de Espera</h2>
                            </div>
                            <span style={{ background: 'var(--PrimaryColorsBack)', color: 'var(--PrimaryColorsTheme)', padding: '2px 10px', borderRadius: '999px', fontWeight: 700, fontSize: '13px' }}>{salaDeEspera.length}</span>
                        </div>

                        {salaDeEspera.length === 0 ? (
                            <p className="text75" style={{ textAlign: 'center', padding: '2rem 0' }}>
                                Nenhum paciente aguardando no momento.
                            </p>
                        ) : (
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                                {salaDeEspera.map(c => (
                                    <div key={c.id} style={{ background: 'white', border: '1px solid var(--LineColor)', borderRadius: '12px', padding: '1rem 1.25rem', boxShadow: 'var(--shadow-sm)' }}>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '0.5rem' }}>
                                            <p style={{ fontWeight: 700, margin: 0, color: 'var(--TextColor)' }}>{c.pacientes?.nome || "—"}</p>
                                            <span style={{ display: 'flex', alignItems: 'center', gap: '4px', color: 'var(--PrimaryColorsTheme)', fontWeight: 700, fontSize: '13px', whiteSpace: 'nowrap' }}>
                                                <Clock size={14} strokeWidth={2.2} /> {c.data_agendada?.slice(11, 16) || "—"}
                                            </span>
                                        </div>
                                        <p className="text75" style={{ margin: '4px 0 0 0', fontSize: '13px' }}>
                                            {c.tipo_atendimento || "Atendimento"}
                                        </p>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </div>

            </main>
        </>
    );
}

export default ReceptionDashboard;

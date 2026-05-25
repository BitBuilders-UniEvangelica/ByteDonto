import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { apiGetPacientes, apiGetConsultas } from "../../services/api";
import { formatCPF, formatPhone, formatDate } from "../../utils/formatters";
import Section from "../../components/section/SectionAuth";
import SideBar from "../../components/bar/SideBar";
import { useSpecialistSidebar } from "../../hooks/useSidebar";

export default function SpecialistListPatients() {
    const { token } = useAuth();
    const [pacientes, setPacientes] = useState([]);
    const [consultas, setConsultas] = useState([]);
    const [busca, setBusca] = useState("");
    const [loading, setLoading] = useState(true);

    const opc_bar = useSpecialistSidebar("patients");

    useEffect(() => {
        Promise.all([
            apiGetPacientes(token).catch(() => []),
            apiGetConsultas(token).catch(() => []),
        ]).then(([p, c]) => {
            setPacientes(Array.isArray(p) ? p : []);
            setConsultas(Array.isArray(c) ? c : []);
        }).finally(() => setLoading(false));
    }, [token]);

    // Última consulta por paciente (data_agendada mais recente)
    const ultimaConsultaPorPaciente = (pacienteId) => {
        const doPaciente = consultas
            .filter(c => c.paciente_id === pacienteId && c.data_agendada)
            .sort((a, b) => String(b.data_agendada).localeCompare(String(a.data_agendada)));
        return doPaciente.length > 0 ? doPaciente[0].data_agendada : null;
    };

    const pacientesFiltrados = pacientes.filter(p => {
        const query = busca.toLowerCase();
        return (
            (p.nome && p.nome.toLowerCase().includes(query)) ||
            (p.cpf && p.cpf.includes(query)) ||
            (p.telefone_whatsapp && p.telefone_whatsapp.includes(query))
        );
    });

    return (
        <>
            <Section type_styles="specialist" />
            <SideBar opc={opc_bar} styles="specialist" />
            
            <main className="mainBar specialist">
                <div style={{display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: "2rem"}}>
                    <div>
                        <h1 style={{margin: '0 0 0.5rem 0', color: 'var(--PrimaryColorsTheme)', fontSize: '28px'}}>Meus Pacientes</h1>
                        <p className="text75">Acesse o acervo de pacientes que já passaram no seu consultório.</p>
                    </div>
                </div>

                <div className="camp-clinic camp-view">
                    <input
                        type="text"
                        placeholder="Buscar prontuário clínico por nome ou CPF..."
                        style={{width: '100%'}}
                        value={busca}
                        onChange={(e) => setBusca(e.target.value)}
                    />

                    <div className="table" style={{marginTop: '2rem'}}>
                        <div className="table-header" style={{gridTemplateColumns: '1.5fr 1fr 1fr 1fr 1fr'}}>
                            <p className="text75">Paciente</p>
                            <p className="text75">Celular</p>
                            <p className="text75">Última Consulta</p>
                            <p className="text75">Status Médico</p>
                            <p className="text75" style={{textAlign: 'right'}}>Ação</p>
                        </div>
                        <div className="table-body">
                            {loading ? (
                                <div style={{padding: '2rem', textAlign: 'center', color: 'var(--TextColor75)'}}>Carregando base de dados...</div>
                            ) : pacientesFiltrados.length === 0 ? (
                                <div style={{padding: '2rem', textAlign: 'center', color: 'var(--TextColor75)'}}>Nenhum paciente designado ainda.</div>
                            ) : (
                                pacientesFiltrados.map((p, idx) => (
                                    <div key={p.id} className="table-row" style={{gridTemplateColumns: '1.5fr 1fr 1fr 1fr 1fr', borderBottom: idx === pacientesFiltrados.length - 1 ? 'none' : '1px solid var(--LineColor)'}}>
                                        <div><p style={{fontWeight: 700}}>{p.nome}</p><span style={{fontSize: '12px', color: 'var(--TextColor75)'}}>{formatCPF(p.cpf)}</span></div>
                                        <p style={{fontFamily: 'var(--font-secondary)'}}>{formatPhone(p.telefone_whatsapp)}</p>
                                        <p>{ultimaConsultaPorPaciente(p.id) ? formatDate(ultimaConsultaPorPaciente(p.id)) : "—"}</p>
                                        <div>
                                            <span style={{
                                                background: p.status === 'Ativo' ? 'var(--WarningBack)' : 'var(--SuccessBack)',
                                                color: p.status === 'Ativo' ? 'var(--WarningText)' : 'var(--SuccessText)',
                                                padding: '4px 10px', borderRadius: '999px', fontSize: '12px', fontWeight: 700
                                            }}>{p.status === 'Ativo' ? "Em Andamento" : "Alta Médica"}</span>
                                        </div>
                                        <div style={{textAlign: 'right'}}>
                                            <Link to={`/specialist/patient/view?id=${p.id}`} className="submit" style={{padding: '6px 16px', fontSize: '13px', background: 'var(--PrimaryColorsBack)', color: 'var(--PrimaryColorsTheme)', boxShadow: 'none', display: 'inline-block', fontWeight: 700}}>Abrir Prontuário</Link>
                                        </div>
                                    </div>
                                ))
                            )}
                        </div>
                    </div>
                </div>
            </main>
        </>
    );
}

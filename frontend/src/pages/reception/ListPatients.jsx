import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { apiGetPacientes, apiGetConsultas } from "../../services/api";
import { formatCPF, formatPhone, formatDate } from "../../utils/formatters";
import Section from "../../components/section/SectionAuth";
import SideBar from "../../components/bar/SideBar";
import { useReceptionSidebar } from "../../hooks/useSidebar";
import { UserPlus } from "lucide-react";
import '../../styles/clinic.css';

/* MAIN COMPONENT */
function ListPatients() {
    const { token } = useAuth();
    const [pacientes, setPacientes] = useState([]);
    const [consultas, setConsultas] = useState([]);
    const [busca, setBusca] = useState("");
    const [loading, setLoading] = useState(true);

    // Menu da recepção
    const opc_bar = useReceptionSidebar("patients");

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
            <Section type_styles="reception" />
            <SideBar opc={opc_bar} styles="reception" />
            
            <main className="mainBar reception">
                <div className="page-header" style={{marginBottom: "2rem"}}>
                    <div>
                        <h1 style={{margin: '0 0 0.5rem 0', color: 'var(--PrimaryColorsTheme)', fontSize: '28px'}}>Pacientes e Prontuários</h1>
                        <p className="text75 page-header-desc">Listagem completa e busca avançada de todos os pacientes da clínica.</p>
                    </div>
                    <div>
                        <Link to="/reception/patient/register" style={{background: 'var(--PrimaryColorsTheme)', color: 'white', padding: '12px 24px', borderRadius: '12px', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '0.5rem', boxShadow: 'var(--shadow-sm)'}}>
                            <UserPlus size={18} strokeWidth={2.5} /> Cadastrar Novo Paciente
                        </Link>
                    </div>
                </div>

                <div className="camp-clinic camp-view camp-compact">
                    <input
                        type="text"
                        placeholder="Buscar por Nome, Telefone ou CPF..."
                        className="search-input"
                        value={busca}
                        onChange={(e) => setBusca(e.target.value)}
                    />

                    <div className="table" style={{marginTop: '2rem'}}>
                        <div className="table-header grid-patients">
                            <p className="text75">Paciente</p>
                            <p className="text75 hide-mobile">Celular</p>
                            <p className="text75 hide-mobile">Última Consulta</p>
                            <p className="text75 hide-mobile">Status</p>
                            <p className="text75" style={{textAlign: 'right'}}>Ação</p>
                        </div>
                        
                        <div className="table-body">
                            {loading ? (
                                <div style={{padding: '2rem', textAlign: 'center', color: 'var(--TextColor75)'}}>Carregando base de dados...</div>
                            ) : pacientesFiltrados.length === 0 ? (
                                <div style={{padding: '2rem', textAlign: 'center', color: 'var(--TextColor75)'}}>Nenhum paciente encontrado. Crie seu primeiro paciente!</div>
                            ) : (
                                pacientesFiltrados.map((p, idx) => (
                                    <div key={p.id} className="table-row grid-patients" style={{borderBottom: idx === pacientesFiltrados.length - 1 ? 'none' : '1px solid var(--LineColor)'}}>
                                        <div><p style={{fontWeight: 700}}>{p.nome}</p><span style={{fontSize: '12px', color: 'var(--TextColor75)'}}>{formatCPF(p.cpf)}</span></div>
                                        <p className="hide-mobile" style={{fontFamily: 'var(--font-secondary)'}}>{formatPhone(p.telefone_whatsapp)}</p>
                                        <p className="hide-mobile">{ultimaConsultaPorPaciente(p.id) ? formatDate(ultimaConsultaPorPaciente(p.id)) : "—"}</p>
                                        <p className="hide-mobile">
                                            {(() => {
                                                const ativo = (p.status || "Ativo") === "Ativo";
                                                return (
                                                    <span style={{background: ativo ? 'var(--SuccessBack)' : 'var(--LineColor)', color: ativo ? 'var(--SuccessText)' : 'var(--TextColor75)', padding: '3px 12px', borderRadius: '999px', fontSize: '12px', fontWeight: 700}}>{p.status || "Ativo"}</span>
                                                );
                                            })()}
                                        </p>
                                        <div style={{textAlign: 'right'}}><Link to={`/reception/patient/view?id=${p.id}`} className="submit" style={{padding: '6px 16px', fontSize: '13px', background: 'var(--PrimaryColorsBack)', color: 'var(--PrimaryColorsTheme)', boxShadow: 'none', border: '1px solid var(--LineColor)', display: 'inline-block'}}>Ver Ficha</Link></div>
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

export default ListPatients;

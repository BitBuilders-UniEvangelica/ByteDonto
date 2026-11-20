import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../../../context/AuthContext";
import { apiGetPacientes } from "../../../services/api";
import { formatCPF, formatPhone, formatDate } from "../../../utils/formatters";
import Section from "../../../components/section/SectionAuth";
import SideBar from "../../../components/bar/SideBar";
import { useSidebar } from "../../../hooks/useSidebar";
import { usePermissao } from "../../../hooks/usePermissao";
import { useRotas } from "../../../hooks/useRotas";
import { UserPlus } from "lucide-react";
import { Banner, BlocoCarregando } from "../../../components/feedback/Feedback";
import Paginacao from "../../../components/paginacao/Paginacao";
import '../../../styles/clinic.css';

const POR_PAGINA = 20;
const VAZIO = { items: [], page: 1, per_page: POR_PAGINA, total: 0 };

const ESTILO_ACAO = {padding: '6px 16px', fontSize: '13px', background: 'var(--PrimaryColorsBack)', color: 'var(--PrimaryColorsTheme)', boxShadow: 'none', border: '1px solid var(--LineColor)', display: 'inline-block'};

/* LISTA DE PACIENTES — mesma tela para Dono, Especialista e Recepção
   (/owner/patients, /specialist/patients, /reception/patients).
   As ações aparecem conforme a permissão de quem está logado:
   - editar_pacientes → "Cadastrar Novo Paciente"
   - ver_prontuario   → "Prontuário" (prontuário clínico)
   - ver_pacientes    → "Ver Ficha" (exigida para abrir a própria tela) */
function ListPatients() {
    const { token } = useAuth();
    const [busca, setBusca] = useState("");            // o que está no campo
    const [buscaAplicada, setBuscaAplicada] = useState(""); // o que foi enviado ao servidor
    const [page, setPage] = useState(1);
    const [tentativa, setTentativa] = useState(0);
    // Resultado da última requisição + a "chave" (página/busca) a que ele pertence.
    const [resultado, setResultado] = useState({ chave: null, dados: VAZIO, erro: false });

    const opc_bar = useSidebar("patients");
    const podeCadastrar = usePermissao("editar_pacientes");
    const podeVerProntuario = usePermissao("ver_prontuario");
    const { estilo, rota } = useRotas();

    const chave = `${page}|${buscaAplicada}|${tentativa}`;
    const loading = resultado.chave !== chave;
    const erroCarregar = resultado.erro;
    const dados = resultado.dados;
    const pacientes = dados.items || [];

    // A busca vai para o servidor 300 ms depois que a pessoa para de digitar,
    // e sempre volta para a primeira página.
    useEffect(() => {
        const t = setTimeout(() => {
            const termo = busca.trim();
            if (termo !== buscaAplicada) {
                setBuscaAplicada(termo);
                setPage(1);
            }
        }, 300);
        return () => clearTimeout(t);
    }, [busca, buscaAplicada]);

    // Só a página pedida é carregada (20 por vez), já filtrada no banco.
    useEffect(() => {
        let ativo = true;
        apiGetPacientes(token, { page, perPage: POR_PAGINA, busca: buscaAplicada })
            .then(d => { if (ativo) setResultado({ chave, dados: d, erro: false }); })
            .catch(() => { if (ativo) setResultado(r => ({ chave, dados: r.dados, erro: true })); });
        return () => { ativo = false; };
    }, [token, page, buscaAplicada, chave]);

    function tentarNovamente() {
        setTentativa(t => t + 1);
    }

    return (
        <>
            <Section type_styles={estilo} />
            <SideBar opc={opc_bar} styles={estilo} />
            
            <main className={`mainBar ${estilo}`}>
                {erroCarregar && (
                    <Banner
                        texto="Não foi possível carregar os pacientes. Verifique sua conexão com a internet."
                        onTentarNovamente={tentarNovamente}
                    />
                )}
                <div className="page-header" style={{marginBottom: "2rem"}}>
                    <div>
                        <h1 style={{margin: '0 0 0.5rem 0', color: 'var(--PrimaryColorsTheme)', fontSize: '28px'}}>Pacientes e Prontuários</h1>
                        <p className="text75 page-header-desc">Listagem completa e busca avançada de todos os pacientes da clínica.</p>
                    </div>
                    {podeCadastrar && (
                    <div>
                        <Link to={rota("patient/register")} style={{ background: 'var(--PrimaryColorsTheme)', color: 'white', padding: '12px 24px', borderRadius: '12px', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '0.5rem', boxShadow: 'var(--shadow-sm)', border: 'none', cursor: 'pointer' }}>
                            <UserPlus size={18} strokeWidth={2.5} /> Cadastrar Novo Paciente
                        </Link>
                    </div>
                    )}
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
                            {loading && resultado.chave === null ? (
                                <BlocoCarregando texto="Carregando pacientes..." />
                            ) : pacientes.length === 0 ? (
                                <div style={{padding: '2rem', textAlign: 'center', color: 'var(--TextColor75)'}}>
                                    {erroCarregar
                                        ? "Lista indisponível no momento. Use “Tentar novamente” no aviso acima."
                                        : buscaAplicada
                                        ? `Nenhum paciente encontrado para "${buscaAplicada}". Confira o nome ou cadastre um novo paciente.`
                                        : podeCadastrar ? "Nenhum paciente encontrado. Crie seu primeiro paciente!" : "Nenhum paciente cadastrado ainda."}
                                </div>
                            ) : (
                                pacientes.map((p, idx) => (
                                    <div key={p.id} className="table-row grid-patients" style={{borderBottom: idx === pacientes.length - 1 ? 'none' : '1px solid var(--LineColor)'}}>
                                        <div><p style={{fontWeight: 700}}>{p.nome}</p><span style={{fontSize: '12px', color: 'var(--TextColor75)'}}>{formatCPF(p.cpf)}</span></div>
                                        <p className="hide-mobile" style={{fontFamily: 'var(--font-secondary)'}}>{formatPhone(p.telefone_whatsapp)}</p>
                                        <p className="hide-mobile">{p.ultima_consulta ? formatDate(p.ultima_consulta) : "—"}</p>
                                        <p className="hide-mobile">
                                            {(() => {
                                                const ativo = (p.status || "Ativo") === "Ativo";
                                                return (
                                                    <span style={{background: ativo ? 'var(--SuccessBack)' : 'var(--LineColor)', color: ativo ? 'var(--SuccessText)' : 'var(--TextColor75)', padding: '3px 12px', borderRadius: '999px', fontSize: '12px', fontWeight: 700}}>{p.status || "Ativo"}</span>
                                                );
                                            })()}
                                        </p>
                                        <div style={{display: 'flex', gap: '6px', justifyContent: 'flex-end', flexWrap: 'wrap'}}>
                                            {podeVerProntuario && (
                                                <Link to={rota(`patient/record?id=${p.id}`)} className="submit" style={{...ESTILO_ACAO, fontWeight: 700}}>Prontuário</Link>
                                            )}
                                            <Link to={rota(`patient/view?id=${p.id}`)} className="submit" style={ESTILO_ACAO}>Ver Ficha</Link>
                                        </div>
                                    </div>
                                ))
                            )}
                        </div>
                    </div>
                    <Paginacao
                        page={page}
                        perPage={dados.per_page || POR_PAGINA}
                        total={dados.total || 0}
                        onMudarPagina={setPage}
                        carregando={loading}
                        rotulo="pacientes"
                    />
                </div>
            </main>
        </>
    );
}

export default ListPatients;

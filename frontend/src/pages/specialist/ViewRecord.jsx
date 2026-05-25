import { useState, useEffect } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { apiGetPaciente, apiAtualizarPaciente } from "../../services/api";
import Section from "../../components/section/SectionAuth";
import SideBar from "../../components/bar/SideBar";
import { useSpecialistSidebar } from "../../hooks/useSidebar";
import Odontograma from "../../components/odontograma/Odontograma";
import RegistroClinico from "../../components/registro/RegistroClinico";
import PlanoDeTratamento from "../../components/plano/PlanoDeTratamento";
import GaleriaImagens from "../../components/imagens/GaleriaImagens";
import { UserRound, Printer, Plus, X, AlertTriangle, Check } from "lucide-react";
import "../../styles/clinic.css";
import "../../styles/Forms.css";
import { formatDate, calcIdade } from "../../utils/formatters";

function Receituario({ paciente, dentista }) {
    const [medicamentos, setMedicamentos] = useState([{ nome:"", posologia:"", duracao:"" }]);
    const [orientacoes, setOrientacoes] = useState("");

    function addMed() { setMedicamentos(p=>[...p,{nome:"",posologia:"",duracao:""}]); }
    function removeMed(i) { setMedicamentos(p=>p.filter((_,j)=>j!==i)); }
    function updateMed(i,f,v) { setMedicamentos(p=>p.map((m,j)=>j===i?{...m,[f]:v}:m)); }

    function imprimir() {
        const w = window.open("","_blank","width=800,height=600");
        const hoje = new Date().toLocaleDateString("pt-BR");
        w.document.write(`
            <html><head><title>Receituário</title><style>
                body{font-family:Arial,sans-serif;max-width:700px;margin:40px auto;color:#111}
                h2{color:#155E75;border-bottom:2px solid #155E75;padding-bottom:8px}
                .med{margin:16px 0;padding:12px;border-left:4px solid #155E75;background:#f8fafc}
                .footer{margin-top:60px;border-top:1px solid #ccc;padding-top:16px;font-size:13px;color:#666}
            </style></head><body>
            <h2>Receituário Odontológico</h2>
            <p><strong>Paciente:</strong> ${paciente?.nome || ""} &nbsp;&nbsp; <strong>Data:</strong> ${hoje}</p>
            ${medicamentos.filter(m=>m.nome).map((m,i)=>`
                <div class="med"><strong>${i+1}. ${m.nome}</strong><br/>
                ${m.posologia?`<span>Posologia: ${m.posologia}</span><br/>`:""}
                ${m.duracao?`<span>Duração: ${m.duracao}</span>`:""}
                </div>`).join("")}
            ${orientacoes?`<p><strong>Orientações:</strong><br/>${orientacoes.replace(/\n/g,"<br/>")}</p>`:""}
            <div class="footer">
                <p>Dr(a). ${dentista || ""}</p>
                <div style="margin-top:40px;border-top:1px solid #999;width:280px;text-align:center;padding-top:8px">Assinatura</div>
            </div>
            </body></html>`);
        w.document.close();
        w.print();
    }

    return (
        <div>
            <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:"1.5rem"}}>
                <div>
                    <h3 style={{margin:"0 0 4px 0",color:"var(--PrimaryColorsTheme)"}}>Receituário</h3>
                    <p style={{margin:0,fontSize:"13px",color:"var(--TextColor75)"}}>Preencha e imprima uma prescrição para o paciente.</p>
                </div>
                <button onClick={imprimir} style={{display:"flex",alignItems:"center",gap:"8px",padding:"10px 24px",background:"var(--PrimaryColorsTheme)",color:"white",border:"none",borderRadius:"var(--radius-md)",fontWeight:700,cursor:"pointer"}}>
                    <Printer size={18} strokeWidth={2} /> Imprimir Receituário
                </button>
            </div>

            <div style={{display:"flex",flexDirection:"column",gap:"12px",marginBottom:"1.5rem"}}>
                {medicamentos.map((m,i)=>(
                    <div key={i} style={{display:"grid",gridTemplateColumns:"2fr 2fr 1fr 36px",gap:"8px",background:"var(--ThemeColor)",border:"1px solid var(--LineColor)",borderRadius:"var(--radius-md)",padding:"12px",alignItems:"center"}}>
                        <input value={m.nome} onChange={e=>updateMed(i,"nome",e.target.value)} placeholder="Medicamento (ex: Amoxicilina 500mg)" style={{padding:"8px 10px",borderRadius:"var(--radius-sm)",border:"1px solid var(--LineColor)",fontSize:"13px"}} />
                        <input value={m.posologia} onChange={e=>updateMed(i,"posologia",e.target.value)} placeholder="Posologia (ex: 1 comprimido 8/8h)" style={{padding:"8px 10px",borderRadius:"var(--radius-sm)",border:"1px solid var(--LineColor)",fontSize:"13px"}} />
                        <input value={m.duracao} onChange={e=>updateMed(i,"duracao",e.target.value)} placeholder="Duração (ex: 7 dias)" style={{padding:"8px 10px",borderRadius:"var(--radius-sm)",border:"1px solid var(--LineColor)",fontSize:"13px"}} />
                        <button aria-label="Remover medicamento" onClick={()=>removeMed(i)} style={{background:"var(--DangerBack)",color:"var(--DangerText)",border:"none",borderRadius:"var(--radius-sm)",width:"36px",height:"36px",cursor:"pointer",display:"flex",alignItems:"center",justifyContent:"center"}}><X size={16} strokeWidth={2.5} /></button>
                    </div>
                ))}
                <button onClick={addMed} style={{display:"flex",alignItems:"center",gap:"6px",alignSelf:"flex-start",fontSize:"13px",color:"var(--PrimaryColorsTheme)",background:"none",border:"1px dashed var(--PrimaryColorsTheme)",borderRadius:"var(--radius-sm)",padding:"8px 14px",cursor:"pointer",fontWeight:600}}>
                    <Plus size={16} strokeWidth={2.5} /> Adicionar medicamento
                </button>
            </div>

            <div>
                <p style={{margin:"0 0 6px 0",fontWeight:700,fontSize:"13px",color:"var(--TextColor75)"}}>Orientações Gerais</p>
                <textarea value={orientacoes} onChange={e=>setOrientacoes(e.target.value)} rows={3} placeholder="Ex: Evitar alimentos duros nas próximas 24h, não fumar..." style={{width:"100%",padding:"10px 12px",borderRadius:"8px",border:"1px solid var(--LineColor)",fontSize:"14px",resize:"vertical",fontFamily:"inherit",boxSizing:"border-box"}} />
            </div>
        </div>
    );
}

export default function SpecialistViewRecord() {
    const { token, user } = useAuth();
    const [searchParams] = useSearchParams();
    const pacienteId = searchParams.get("id");

    const [paciente, setPaciente] = useState(null);
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState("historico");
    const [anamneseForm, setAnamneseForm] = useState({});
    const [salvandoAnamnese, setSalvandoAnamnese] = useState(false);
    const [anamneseSucesso, setAnamneseSucesso] = useState(false);
    const [odontograma, setOdontograma] = useState({});
    const [salvandoOdontograma, setSalvandoOdontograma] = useState(false);
    const [odontogramaSucesso, setOdontogramaSucesso] = useState(false);
    // Quando o dentista usa "+ Adicionar ao Plano" no odontograma, guardamos o
    // item aqui e a aba do plano abre o formulário já pré-preenchido.
    const [itemSugeridoPlano, setItemSugeridoPlano] = useState(null);

    const opc_bar = useSpecialistSidebar("patients");

    useEffect(() => {
        if (!pacienteId) {
            setLoading(false);
            return;
        }

        const fetchPaciente = async () => {
            try {
                const data = await apiGetPaciente(token, pacienteId);
                setPaciente(data);
                setAnamneseForm(data.anamnese || {});
                setOdontograma(data.odontograma || {});
            } catch (error) {
                console.error("Erro ao buscar paciente", error);
            } finally {
                setLoading(false);
            }
        };

        fetchPaciente();
    }, [pacienteId, token]);

    async function handleSalvarAnamnese(e) {
        e.preventDefault();
        setSalvandoAnamnese(true);
        setAnamneseSucesso(false);
        try {
            await apiAtualizarPaciente(token, pacienteId, { anamnese: anamneseForm });
            setPaciente(prev => ({ ...prev, anamnese: anamneseForm }));
            setAnamneseSucesso(true);
            setTimeout(() => setAnamneseSucesso(false), 2000);
        } catch (err) {
            alert(`Erro ao salvar: ${err.message}`);
        } finally {
            setSalvandoAnamnese(false);
        }
    }

    async function handleSalvarOdontograma() {
        setSalvandoOdontograma(true);
        setOdontogramaSucesso(false);
        try {
            await apiAtualizarPaciente(token, pacienteId, { odontograma });
            setPaciente(prev => ({ ...prev, odontograma }));
            setOdontogramaSucesso(true);
            setTimeout(() => setOdontogramaSucesso(false), 2000);
        } catch (err) {
            alert(`Erro ao salvar odontograma: ${err.message}`);
        } finally {
            setSalvandoOdontograma(false);
        }
    }

    if (loading) {
        return (
            <>
                <Section type_styles="specialist" />
                <SideBar opc={opc_bar} styles="specialist" />
                <main className="mainBar specialist"><p>Carregando prontuário...</p></main>
            </>
        );
    }

    if (!paciente) {
        return (
            <>
                <Section type_styles="specialist" />
                <SideBar opc={opc_bar} styles="specialist" />
                <main className="mainBar specialist"><p>Prontuário não encontrado. Retorne à listagem.</p></main>
            </>
        );
    }

    const anamnese = paciente.anamnese || {};

    return (
        <>
            <Section type_styles="specialist" />
            <SideBar opc={opc_bar} styles="specialist" />
            
            <main className="mainBar specialist">
                {/* CABEÇALHO CLÍNICO DO DENTISTA */}
                <div style={{background: 'var(--PrimaryColorsTheme)', borderRadius: 'var(--radius-lg)', padding: '2rem', color: 'white', display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem'}}>
                    <div style={{display: 'flex', gap: '1.5rem', alignItems: 'center'}}>
                        <div style={{width: '72px', height: '72px', borderRadius: '50%', background: 'rgba(255,255,255,0.15)', color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0}}>
                            <UserRound size={36} strokeWidth={1.8} />
                        </div>
                        <div>
                            <div style={{display: 'flex', alignItems: 'center', gap: '1rem'}}>
                                <h1 style={{margin: '0', fontSize: '26px', color: 'white'}}>{paciente.nome}</h1>
                                <span style={{background: 'rgba(255,255,255,0.18)', padding: '4px 12px', borderRadius: '999px', fontSize: '12px', fontWeight: 700}}>Em Tratamento</span>
                            </div>
                            <div style={{display: 'flex', gap: '2rem', marginTop: '0.75rem', fontFamily: 'var(--font-secondary)'}}>
                                <span style={{fontSize: '13px', fontWeight: 500}}><strong style={{opacity: 0.7, fontWeight: 700}}>Nascimento:</strong> {formatDate(paciente.data_nascimento)} ({calcIdade(paciente.data_nascimento)} anos)</span>
                            </div>
                        </div>
                    </div>
                </div>

                {/* CONTROLE DE ABAS DO DENTISTA */}
                <ul className="tabs-bar specialist" style={{marginBottom: '2rem'}}>
                    <li className={activeTab === "historico" ? "select" : ""} onClick={() => setActiveTab("historico")}>Evolução Prontuário</li>
                    <li className={activeTab === "odontograma" ? "select" : ""} onClick={() => setActiveTab("odontograma")}>Odontograma</li>
                    <li className={activeTab === "plano" ? "select" : ""} onClick={() => setActiveTab("plano")}>Plano de Tratamento</li>
                    <li className={activeTab === "anamnese" ? "select" : ""} onClick={() => setActiveTab("anamnese")}>Ficha Médica Base</li>
                    <li className={activeTab === "receituario" ? "select" : ""} onClick={() => setActiveTab("receituario")}>Receituário</li>
                    <li className={activeTab === "arquivos" ? "select" : ""} onClick={() => setActiveTab("arquivos")}>Imagens e Raio-X</li>
                </ul>

                {/* ABA 1: EVOLUÇÃO */}
                {activeTab === "historico" && (
                    <div className="forms-section" style={{animation: 'fadeIn 0.3s', padding: 0}}>
                        <div style={{display: 'grid', gridTemplateColumns: '1fr 300px', gap: '2rem', padding: '0 2rem 2rem 2rem'}}>
                            <div>
                                <h3 style={{color: 'var(--TextColor)', margin: '0 0 1.5rem 0'}}>Timeline de Tratamentos</h3>
                                <RegistroClinico pacienteId={pacienteId} token={token} />
                            </div>

                            <div>
                                <h3 style={{color: 'var(--TextColor)', margin: '0 0 1.5rem 0'}}>Avisos Críticos</h3>
                                {anamnese.alergias ? (
                                    <div style={{background: 'var(--DangerBack)', border: '1px solid var(--LineColor)', padding: '1rem', borderRadius: 'var(--radius-md)', marginBottom: '1rem', color: 'var(--DangerText)'}}>
                                        <strong style={{display: 'flex', alignItems: 'center', gap: '6px'}}><AlertTriangle size={16} strokeWidth={2.5} /> Alergia Médica:</strong>
                                        <p style={{margin: '4px 0 0 0', fontSize: '14px', color: 'var(--DangerText)'}}>{anamnese.alergias}</p>
                                    </div>
                                ) : null}

                                {anamnese.condicoes ? (
                                    <div style={{background: 'var(--WarningBack)', border: '1px solid var(--LineColor)', padding: '1rem', borderRadius: 'var(--radius-md)', color: 'var(--WarningText)'}}>
                                        <strong style={{display: 'flex', alignItems: 'center', gap: '6px'}}><AlertTriangle size={16} strokeWidth={2.5} /> Doença Sistêmica:</strong>
                                        <p style={{margin: '4px 0 0 0', fontSize: '14px', color: 'var(--WarningText)'}}>{anamnese.condicoes}</p>
                                    </div>
                                ) : null}

                                {(!anamnese.alergias && !anamnese.condicoes) && (
                                    <p style={{fontSize: '13px', color: 'var(--TextColor75)'}}>Ficha verde. Nenhum alerta.</p>
                                )}
                            </div>
                        </div>
                    </div>
                )}

                {/* ABA 2: ODONTOGRAMA */}
                {activeTab === "odontograma" && (
                    <div className="forms-section" style={{animation: 'fadeIn 0.3s'}}>
                        <h3 style={{color: 'var(--PrimaryColorsTheme)', margin: '0 0 0.5rem 0'}}>Odontograma (Notação FDI)</h3>
                        <p className="text75" style={{marginBottom: '1.5rem'}}>Clique em cada dente para registrar seu status clínico. Salve ao terminar.</p>

                        <Odontograma
                            dados={odontograma}
                            onChange={setOdontograma}
                            readOnly={false}
                            onAdicionarAoPlano={(item) => {
                                setItemSugeridoPlano(item);
                                setActiveTab("plano");
                            }}
                        />

                        <div style={{display: 'flex', alignItems: 'center', gap: '1rem', marginTop: '1.5rem'}}>
                            <button
                                onClick={handleSalvarOdontograma}
                                disabled={salvandoOdontograma}
                                className="submit"
                                style={{
                                    background: 'var(--PrimaryColorsTheme)',
                                    color: 'white',
                                    padding: '12px 28px',
                                    borderRadius: 'var(--radius-md)',
                                    border: 'none',
                                    fontWeight: 700,
                                    fontSize: '14px',
                                    opacity: salvandoOdontograma ? 0.7 : 1,
                                    cursor: salvandoOdontograma ? 'not-allowed' : 'pointer',
                                }}
                            >
                                {salvandoOdontograma ? 'Salvando...' : 'Salvar Odontograma'}
                            </button>
                            {odontogramaSucesso && (
                                <span style={{color: 'var(--SuccessText)', fontWeight: 700, fontSize: '14px', display: 'flex', alignItems: 'center', gap: '6px'}}>
                                    <Check size={16} strokeWidth={2.5} /> Salvo com sucesso!
                                </span>
                            )}
                        </div>
                    </div>
                )}
                
                {/* ABA 3: PLANO DE TRATAMENTO */}
                {activeTab === "plano" && (
                    <div className="forms-section" style={{animation: 'fadeIn 0.3s'}}>
                        <h3 style={{color: 'var(--PrimaryColorsTheme)', margin: '0 0 0.5rem 0'}}>Plano de Tratamento</h3>
                        <p className="text75" style={{marginBottom: '1.5rem'}}>Crie orçamentos e acompanhe a evolução de cada procedimento.</p>
                        <PlanoDeTratamento
                            pacienteId={pacienteId}
                            token={token}
                            itemInicial={itemSugeridoPlano}
                            onConsumirItemInicial={() => setItemSugeridoPlano(null)}
                        />
                    </div>
                )}

                {/* ABA 4: ANAMNESE */}
                {activeTab === "anamnese" && (
                     <div className="forms-section" style={{animation: 'fadeIn 0.3s'}}>
                        <h3 style={{color: 'var(--PrimaryColorsTheme)', margin: '0 0 1.5rem 0'}}>Anamnese (Editável pelo Especialista)</h3>
                        <p className="text75" style={{marginBottom: '2rem'}}>Somente a equipe médica pode alterar esses campos fundamentais.</p>

                        <form onSubmit={handleSalvarAnamnese}>
                            <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem'}}>
                                <div>
                                    <p style={{fontWeight: 700, margin: '0 0 8px 0', color: 'var(--TextColor75)'}}>Condições Sistêmicas (Doenças)?</p>
                                    <textarea style={{width: '100%', marginBottom: '24px'}} rows="2"
                                        value={anamneseForm.condicoes || ""}
                                        onChange={e => setAnamneseForm(p => ({ ...p, condicoes: e.target.value }))} />

                                    <p style={{fontWeight: 700, margin: '0 0 8px 0', color: 'var(--TextColor75)'}}>Medicações em Uso Contínuo?</p>
                                    <textarea style={{width: '100%', marginBottom: '24px'}} rows="2"
                                        value={anamneseForm.medicacoes || ""}
                                        onChange={e => setAnamneseForm(p => ({ ...p, medicacoes: e.target.value }))} />
                                </div>
                                <div>
                                    <p style={{fontWeight: 700, margin: '0 0 8px 0', color: 'var(--TextColor75)'}}>Alergias a Medicamentos/Outros?</p>
                                    <textarea style={{width: '100%', marginBottom: '24px'}} rows="2"
                                        value={anamneseForm.alergias || ""}
                                        onChange={e => setAnamneseForm(p => ({ ...p, alergias: e.target.value }))} />

                                    <p style={{fontWeight: 700, margin: '0 0 8px 0', color: 'var(--TextColor75)'}}>Cirurgias Prévias</p>
                                    <textarea style={{width: '100%', marginBottom: '24px'}} rows="2"
                                        value={anamneseForm.cirurgias || ""}
                                        onChange={e => setAnamneseForm(p => ({ ...p, cirurgias: e.target.value }))} />
                                </div>
                            </div>

                            <div style={{display: 'flex', alignItems: 'center', gap: '1rem', marginTop: '1rem'}}>
                                <button type="submit" className="submit" disabled={salvandoAnamnese}>
                                    {salvandoAnamnese ? "Salvando..." : "Atualizar Ficha Médica"}
                                </button>
                                {anamneseSucesso && <span style={{color: 'var(--SuccessText)', fontWeight: 700, fontSize: '14px', display: 'flex', alignItems: 'center', gap: '6px'}}><Check size={16} strokeWidth={2.5} /> Salvo com sucesso!</span>}
                            </div>
                        </form>
                    </div>
                )}
                
                {/* ABA 5: RECEITUÁRIO */}
                {activeTab === "receituario" && (
                    <div className="forms-section" style={{animation: 'fadeIn 0.3s'}}>
                        <Receituario paciente={paciente} dentista={user?.perfil?.nome} />
                    </div>
                )}

                {/* ABA 6: IMAGENS E RAIO-X */}
                {activeTab === "arquivos" && (
                    <div className="forms-section" style={{animation: 'fadeIn 0.3s'}}>
                        <GaleriaImagens pacienteId={pacienteId} token={token} />
                    </div>
                )}

            </main>
        </>
    );
}

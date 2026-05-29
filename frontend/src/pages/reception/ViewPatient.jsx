import { useState, useEffect } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import {
    apiGetPaciente,
    apiGetImagens,
    apiUploadImagem,
    apiDeletarImagem,
    apiGetFinanceiro,
    apiCriarLancamento,
    apiGetConsultas,
} from "../../services/api";
import Section from "../../components/section/SectionAuth";
import SideBar from "../../components/bar/SideBar";
import { useReceptionSidebar } from "../../hooks/useSidebar";
import { usePermissao } from "../../hooks/usePermissao";
import TermoConsentimento from "../../components/consentimento/TermoConsentimento";
import { UserRound, Upload, FileText, AlertTriangle, X, Pencil, Stethoscope } from "lucide-react";
import "../../styles/clinic.css";
import "../../styles/Forms.css";
import { formatCPF, formatPhone, formatDate, idadeLabel, formatCurrency } from "../../utils/formatters";

export default function ViewPatient() {
    const { token } = useAuth();
    const [searchParams] = useSearchParams();
    const pacienteId = searchParams.get("id");
    
    const [paciente, setPaciente] = useState(null);
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState("historico");

    // Arquivos & Imagens
    const [imagens, setImagens] = useState([]);
    const [imagensLoading, setImagensLoading] = useState(false);
    const [imagensErro, setImagensErro] = useState("");
    const [uploading, setUploading] = useState(false);

    // Financeiro
    const [lancamentos, setLancamentos] = useState([]);
    const [financeiroLoading, setFinanceiroLoading] = useState(false);
    const [procedimento, setProcedimento] = useState("");
    const [valorCobranca, setValorCobranca] = useState("");
    const [formaPagamento, setFormaPagamento] = useState("Pix");
    const [statusPagamento, setStatusPagamento] = useState("Pago");
    const [salvandoCobranca, setSalvandoCobranca] = useState(false);
    const [cobrancaErro, setCobrancaErro] = useState("");

    // Histórico — timeline de atendimentos
    const [atendimentos, setAtendimentos] = useState([]);

    // Menu da recepção
    const opc_bar = useReceptionSidebar("patients");

    // Acesso ao prontuário clínico (odontograma, plano de tratamento).
    // Disponível para o Dono e para quem tiver a permissão "ver_prontuario".
    const podeVerProntuario = usePermissao("ver_prontuario");

    useEffect(() => {
        if (!pacienteId) {
            setLoading(false);
            return;
        }

        const fetchPaciente = async () => {
            try {
                const data = await apiGetPaciente(token, pacienteId);
                setPaciente(data);
            } catch (error) {
                console.error("Erro ao buscar paciente", error);
            } finally {
                setLoading(false);
            }
        };

        fetchPaciente();
    }, [pacienteId, token]);

    const carregarImagens = async () => {
        if (!pacienteId) return;
        setImagensLoading(true);
        setImagensErro("");
        try {
            const data = await apiGetImagens(token, pacienteId);
            setImagens(Array.isArray(data) ? data : []);
        } catch (error) {
            console.error("Erro ao buscar imagens", error);
            setImagensErro("Não foi possível carregar os arquivos.");
        } finally {
            setImagensLoading(false);
        }
    };

    const carregarFinanceiro = async () => {
        if (!pacienteId) return;
        setFinanceiroLoading(true);
        try {
            const data = await apiGetFinanceiro(token);
            const lista = Array.isArray(data) ? data : [];
            setLancamentos(
                lista.filter(l => String(l.paciente_id) === String(pacienteId))
            );
        } catch (error) {
            console.error("Erro ao buscar financeiro", error);
        } finally {
            setFinanceiroLoading(false);
        }
    };

    const carregarAtendimentos = async () => {
        if (!pacienteId) return;
        try {
            const data = await apiGetConsultas(token);
            const lista = Array.isArray(data) ? data : [];
            const doPaciente = lista
                .filter(c => String(c.paciente_id) === String(pacienteId))
                .sort((a, b) => new Date(b.data_agendada) - new Date(a.data_agendada));
            setAtendimentos(doPaciente);
        } catch (error) {
            console.error("Erro ao buscar atendimentos", error);
        }
    };

    // Carrega dados conforme a aba ativa
    useEffect(() => {
        if (!pacienteId) return;
        if (activeTab === "arquivos") carregarImagens();
        if (activeTab === "financeiro") carregarFinanceiro();
        if (activeTab === "historico") carregarAtendimentos();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [activeTab, pacienteId, token]);

    const handleUpload = async (e) => {
        const file = e.target.files && e.target.files[0];
        e.target.value = "";
        if (!file) return;
        setUploading(true);
        setImagensErro("");
        try {
            await apiUploadImagem(token, pacienteId, file);
            await carregarImagens();
        } catch (error) {
            console.error("Erro no upload", error);
            setImagensErro("Não foi possível enviar o arquivo. Verifique se o armazenamento está configurado.");
        } finally {
            setUploading(false);
        }
    };

    const handleDeletarImagem = async (imagemId) => {
        setImagensErro("");
        try {
            await apiDeletarImagem(token, imagemId);
            await carregarImagens();
        } catch (error) {
            console.error("Erro ao deletar imagem", error);
            setImagensErro("Não foi possível remover o arquivo.");
        }
    };

    const handleSalvarCobranca = async () => {
        setCobrancaErro("");
        const valor = Number(String(valorCobranca).replace(",", "."));
        if (!valor || valor <= 0) {
            setCobrancaErro("Informe um valor válido maior que zero.");
            return;
        }
        setSalvandoCobranca(true);
        try {
            await apiCriarLancamento(token, {
                paciente_id: pacienteId,
                valor,
                forma_pagamento: formaPagamento,
                status_pagamento: statusPagamento,
                descricao: procedimento || undefined,
            });
            setProcedimento("");
            setValorCobranca("");
            setFormaPagamento("Pix");
            setStatusPagamento("Pago");
            await carregarFinanceiro();
        } catch (error) {
            console.error("Erro ao salvar cobrança", error);
            setCobrancaErro(error.message || "Não foi possível salvar a cobrança.");
        } finally {
            setSalvandoCobranca(false);
        }
    };

    if (loading) {
        return (
            <>
                <Section type_styles="reception" />
                <SideBar opc={opc_bar} styles="reception" />
                <main className="mainBar reception"><p>Carregando perfil do paciente...</p></main>
            </>
        );
    }

    if (!paciente) {
        return (
            <>
                <Section type_styles="reception" />
                <SideBar opc={opc_bar} styles="reception" />
                <main className="mainBar reception"><p>Paciente não encontrado. Retorne à listagem.</p></main>
            </>
        );
    }

    // Extrair JSONB Anamnese (Fallback para vazio se não existir)
    const anamnese = paciente.anamnese || {};

    return (
        <>
            <Section type_styles="reception" />
            <SideBar opc={opc_bar} styles="reception" />
            
            <main className="mainBar reception">
                {/* CABEÇALHO DO PRONTUÁRIO */}
                <div style={{background: 'var(--PrimaryColorsTheme)', borderRadius: '16px', padding: '2rem', color: 'white', display: 'flex', alignItems: 'center', gap: '2rem', marginBottom: '2rem', boxShadow: 'var(--shadow-sm)'}}>
                    <div style={{width: '84px', height: '84px', borderRadius: '50%', background: 'rgba(255,255,255,0.15)', border: '1px solid rgba(255,255,255,0.25)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0}}>
                        <UserRound size={40} strokeWidth={1.8} color="white" />
                    </div>
                    <div style={{flex: 1}}>
                        <div style={{display: 'flex', alignItems: 'center', gap: '1rem'}}>
                            <h1 style={{margin: '0', fontSize: '26px', color: 'white'}}>{paciente.nome}</h1>
                            <span style={{background: 'rgba(255,255,255,0.18)', padding: '4px 12px', borderRadius: '999px', fontSize: '12px', fontWeight: 600}}>{paciente.status}</span>
                        </div>
                        <div style={{display: 'flex', gap: '2rem', marginTop: '0.75rem', fontFamily: 'var(--font-secondary)', flexWrap: 'wrap'}}>
                            <span style={{fontSize: '13px', fontWeight: 500}}><strong style={{opacity: 0.75, fontWeight: 700}}>CPF:</strong> {formatCPF(paciente.cpf)}</span>
                            <span style={{fontSize: '13px', fontWeight: 500}}><strong style={{opacity: 0.75, fontWeight: 700}}>Nascimento:</strong> {formatDate(paciente.data_nascimento)}{idadeLabel(paciente.data_nascimento)}</span>
                            <span style={{fontSize: '13px', fontWeight: 500}}><strong style={{opacity: 0.75, fontWeight: 700}}>WhatsApp:</strong> {formatPhone(paciente.telefone_whatsapp)}</span>
                        </div>
                    </div>
                    <div style={{display: 'flex', alignItems: 'center', gap: '0.75rem', flexShrink: 0}}>
                        {podeVerProntuario && (
                            <Link
                                to={`/specialist/patient/view?id=${pacienteId}`}
                                style={{display: 'inline-flex', alignItems: 'center', gap: '8px', background: 'rgba(255,255,255,0.15)', border: '1px solid rgba(255,255,255,0.35)', color: 'white', padding: '10px 18px', borderRadius: '999px', fontSize: '14px', fontWeight: 700, textDecoration: 'none'}}
                            >
                                <Stethoscope size={16} strokeWidth={2.2} /> Prontuário Clínico
                            </Link>
                        )}
                        <Link
                            to={`/reception/patient/register?id=${pacienteId}`}
                            style={{display: 'inline-flex', alignItems: 'center', gap: '8px', background: 'white', color: 'var(--PrimaryColorsTheme)', padding: '10px 18px', borderRadius: '999px', fontSize: '14px', fontWeight: 700, textDecoration: 'none', boxShadow: 'var(--shadow-sm)'}}
                        >
                            <Pencil size={16} strokeWidth={2.2} /> Editar Paciente
                        </Link>
                    </div>
                </div>

                {/* CONTROLE DE ABAS */}
                <ul className="tabs-bar" style={{marginBottom: '2rem'}}>
                    <li className={activeTab === "historico" ? "select" : ""} onClick={() => setActiveTab("historico")}>Histórico & Odontograma</li>
                    <li className={activeTab === "anamnese" ? "select" : ""} onClick={() => setActiveTab("anamnese")}>Anamnese (Ficha Médica)</li>
                    <li className={activeTab === "termos" ? "select" : ""} onClick={() => setActiveTab("termos")}>Termos de Consentimento</li>
                    <li className={activeTab === "arquivos" ? "select" : ""} onClick={() => setActiveTab("arquivos")}>Arquivos & Imagens</li>
                    <li className={activeTab === "financeiro" ? "select" : ""} onClick={() => setActiveTab("financeiro")}>Financeiro e Cobranças</li>
                </ul>

                {/* ABA 1: HISTÓRICO CLINICO */}
                {activeTab === "historico" && (
                    <div className="forms-section" style={{animation: 'fadeIn 0.3s', padding: 0}}>
                        <div style={{display: 'grid', gridTemplateColumns: '1fr 300px', gap: '2rem'}}>
                            {/* LINHA DO TEMPO */}
                            <div>
                                <h3 style={{color: 'var(--PrimaryColorsTheme)', margin: '0 0 1.5rem 0'}}>Timeline de Atendimentos</h3>
                                {atendimentos.length === 0 ? (
                                    <p style={{color: 'var(--TextColor75)'}}>Nenhum atendimento registrado ainda.</p>
                                ) : (
                                    atendimentos.map((c) => {
                                        const cor = c.status === "Finalizado" ? "var(--SuccessText)"
                                            : c.status === "Cancelado" ? "var(--DangerText)"
                                            : "var(--PrimaryColors)";
                                        return (
                                            <div key={c.id} style={{borderLeft: `4px solid ${cor}`, paddingLeft: '1rem', marginBottom: '1rem'}}>
                                                <p style={{margin: '0 0 4px 0', fontWeight: 700}}>
                                                    {c.tipo_atendimento || "Atendimento"} — {c.status || "Agendado"}
                                                </p>
                                                <p style={{margin: 0, color: 'var(--TextColor75)', fontSize: '13px'}}>
                                                    {formatDate(c.data_agendada)}
                                                </p>
                                                {c.evolucao_clinica ? (
                                                    <p style={{margin: '4px 0 0 0', fontSize: '13px'}}>{c.evolucao_clinica}</p>
                                                ) : null}
                                            </div>
                                        );
                                    })
                                )}
                            </div>

                            {/* ALERTAS */}
                            <div>
                                <h3 style={{color: 'var(--PrimaryColorsTheme)', margin: '0 0 1.5rem 0'}}>Alertas Médicos</h3>
                                {anamnese.alergias ? (
                                    <div style={{background: 'var(--DangerBack)', border: '1px solid var(--DangerText)', padding: '1rem', borderRadius: '12px', marginBottom: '1rem', color: 'var(--DangerText)'}}>
                                        <strong style={{display: 'flex', alignItems: 'center', gap: '6px'}}><AlertTriangle size={16} strokeWidth={2} /> Alergia Medicamentosa</strong>
                                        <p style={{margin: '4px 0 0 0', fontSize: '14px'}}>{anamnese.alergias}</p>
                                    </div>
                                ) : null}

                                {anamnese.condicoes ? (
                                    <div style={{background: 'var(--WarningBack)', border: '1px solid var(--WarningText)', padding: '1rem', borderRadius: '12px', color: 'var(--WarningText)'}}>
                                        <strong style={{display: 'flex', alignItems: 'center', gap: '6px'}}><AlertTriangle size={16} strokeWidth={2} /> Condição Sistêmica</strong>
                                        <p style={{margin: '4px 0 0 0', fontSize: '14px'}}>{anamnese.condicoes}</p>
                                    </div>
                                ) : null}

                                {(!anamnese.alergias && !anamnese.condicoes) && (
                                    <p style={{fontSize: '13px', color: 'var(--TextColor75)'}}>Nenhum alerta crítico reportado na anamnese inicial.</p>
                                )}
                            </div>
                        </div>
                    </div>
                )}

                {/* ABA 2: ANAMNESE COMPLETA (Dinâmica via JSONB) */}
                {activeTab === "anamnese" && (
                    <div className="forms-section" style={{animation: 'fadeIn 0.3s'}}>
                        <h3 style={{color: 'var(--PrimaryColorsTheme)', margin: '0 0 1.5rem 0'}}>Registro Sistêmico</h3>
                        <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem'}}>
                            <div>
                                <p style={{fontWeight: 700, margin: '0 0 8px 0', color: 'var(--TextColor75)'}}>Condições Sistêmicas (Doenças)?</p>
                                <p style={{margin: '0 0 24px 0'}}>{anamnese.condicoes || "Negado."}</p>

                                <p style={{fontWeight: 700, margin: '0 0 8px 0', color: 'var(--TextColor75)'}}>Medicações em Uso Contínuo?</p>
                                <p style={{margin: '0 0 24px 0'}}>{anamnese.medicacoes || "Nega uso."}</p>
                                
                                <p style={{fontWeight: 700, margin: '0 0 8px 0', color: 'var(--TextColor75)'}}>Uso de Drogas, Fumo ou Álcool?</p>
                                <p style={{margin: '0 0 24px 0'}}>{anamnese.drogas || "Nenhum."}</p>
                            </div>
                            <div>
                                <p style={{fontWeight: 700, margin: '0 0 8px 0', color: 'var(--TextColor75)'}}>Alergias a Medicamentos/Outros?</p>
                                <p style={{margin: '0 0 24px 0', color: anamnese.alergias ? 'var(--DangerText)' : 'inherit', fontWeight: anamnese.alergias ? 700 : 400}}>{anamnese.alergias || "Nega alergias conhecidas."}</p>

                                <p style={{fontWeight: 700, margin: '0 0 8px 0', color: 'var(--TextColor75)'}}>Cirurgias e Hemorragias Anteriores?</p>
                                <p style={{margin: '0 0 24px 0'}}>{anamnese.cirurgias || "Nenhuma relatada."}</p>

                                <p style={{fontWeight: 700, margin: '0 0 8px 0', color: 'var(--TextColor75)'}}>Contato de Emergência</p>
                                <p style={{margin: '0 0 24px 0'}}>{anamnese.emergencia_nome ? `${anamnese.emergencia_nome} (${formatPhone(anamnese.emergencia_telefone)})` : "-"}</p>
                            </div>
                        </div>

                        <h3 style={{color: 'var(--PrimaryColorsTheme)', margin: '1rem 0 1.5rem 0'}}>Dados Pessoais & Histórico</h3>
                        <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem'}}>
                            <div>
                                <p style={{fontWeight: 700, margin: '0 0 8px 0', color: 'var(--TextColor75)'}}>Naturalidade</p>
                                <p style={{margin: '0 0 24px 0'}}>{anamnese.naturalidade || "-"}</p>

                                <p style={{fontWeight: 700, margin: '0 0 8px 0', color: 'var(--TextColor75)'}}>Nome da Mãe</p>
                                <p style={{margin: '0 0 24px 0'}}>{anamnese.nome_mae || "-"}</p>

                                <p style={{fontWeight: 700, margin: '0 0 8px 0', color: 'var(--TextColor75)'}}>Profissão</p>
                                <p style={{margin: '0 0 24px 0'}}>{anamnese.profissao || "-"}</p>

                                <p style={{fontWeight: 700, margin: '0 0 8px 0', color: 'var(--TextColor75)'}}>Peso / Altura</p>
                                <p style={{margin: '0 0 24px 0'}}>
                                    {anamnese.peso_kg ? `${anamnese.peso_kg} kg` : "-"}
                                    {anamnese.altura_cm ? ` · ${anamnese.altura_cm} cm` : ""}
                                </p>
                            </div>
                            <div>
                                <p style={{fontWeight: 700, margin: '0 0 8px 0', color: 'var(--TextColor75)'}}>Última Visita ao Dentista</p>
                                <p style={{margin: '0 0 24px 0'}}>{anamnese.ultima_visita_dentista || "-"}</p>

                                <p style={{fontWeight: 700, margin: '0 0 8px 0', color: 'var(--TextColor75)'}}>Em Tratamento Médico?</p>
                                <p style={{margin: '0 0 24px 0'}}>{anamnese.em_tratamento_medico ? `Sim — ${anamnese.tratamento_medico_qual || "não especificado"}` : "Não"}</p>

                                <p style={{fontWeight: 700, margin: '0 0 8px 0', color: 'var(--TextColor75)'}}>Já foi Internado?</p>
                                <p style={{margin: '0 0 24px 0'}}>{anamnese.ja_internado ? `Sim — ${anamnese.internacao_motivo || "motivo não informado"}` : "Não"}</p>

                                <p style={{fontWeight: 700, margin: '0 0 8px 0', color: anamnese.reacao_anestesia ? 'var(--DangerText)' : 'var(--TextColor75)'}}>Reação a Anestesia Odontológica?</p>
                                <p style={{margin: '0 0 24px 0', color: anamnese.reacao_anestesia ? 'var(--DangerText)' : 'inherit', fontWeight: anamnese.reacao_anestesia ? 700 : 400}}>{anamnese.reacao_anestesia ? `Sim — ${anamnese.reacao_anestesia_qual || "reação não especificada"}` : "Nega"}</p>
                            </div>
                        </div>

                        {anamnese.historia_odontologica && (
                            <div style={{marginTop: '1rem'}}>
                                <p style={{fontWeight: 700, margin: '0 0 8px 0', color: 'var(--TextColor75)'}}>História Odontológica</p>
                                <p style={{margin: 0}}>{anamnese.historia_odontologica}</p>
                            </div>
                        )}
                    </div>
                )}

                {/* ABA TERMOS: LGPD + Procedimento */}
                {activeTab === "termos" && (
                    <div className="forms-section" style={{animation: 'fadeIn 0.3s'}}>
                        <TermoConsentimento paciente={paciente} token={token} onArquivado={() => setActiveTab("arquivos")} />
                    </div>
                )}

                {/* ABA 3: ARQUIVOS (Laudos, Raio-X) */}
                {activeTab === "arquivos" && (
                    <div className="forms-section" style={{animation: 'fadeIn 0.3s'}}>
                        <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem'}}>
                            <h3 style={{color: 'var(--PrimaryColorsTheme)', margin: 0}}>Imagens e Laudos</h3>
                            <label className="submit" style={{cursor: uploading ? 'wait' : 'pointer', margin: 0, opacity: uploading ? 0.7 : 1, display: 'inline-flex', alignItems: 'center', gap: '8px'}}>
                                <Upload size={16} strokeWidth={2} /> {uploading ? "Enviando..." : "Fazer Upload Novo"}
                                <input type="file" style={{display: 'none'}} onChange={handleUpload} disabled={uploading} />
                            </label>
                        </div>

                        {imagensErro && (
                            <div style={{background: 'var(--DangerBack)', border: '1px solid var(--DangerText)', padding: '0.75rem 1rem', borderRadius: '12px', color: 'var(--DangerText)', marginBottom: '1.5rem', fontSize: '14px'}}>
                                {imagensErro}
                            </div>
                        )}

                        {imagensLoading ? (
                            <p style={{color: 'var(--TextColor75)'}}>Carregando arquivos...</p>
                        ) : imagens.length === 0 ? (
                            <p style={{color: 'var(--TextColor75)'}}>Nenhum arquivo ou imagem enviado para este paciente.</p>
                        ) : (
                            <div style={{display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1.5rem'}}>
                                {imagens.map((img) => {
                                    const isImagem = /\.(png|jpe?g|gif|webp|bmp|svg)$/i.test(img.nome || img.url || "");
                                    return (
                                        <div key={img.id} style={{border: '1px solid var(--LineColor)', borderRadius: '12px', padding: '1rem', textAlign: 'center', background: 'white', boxShadow: 'var(--shadow-sm)'}}>
                                            <a href={img.url} target="_blank" rel="noopener noreferrer" style={{textDecoration: 'none'}}>
                                                <div style={{width: '100%', height: '120px', background: 'var(--BackColor)', borderRadius: '8px', marginBottom: '1rem', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--TextColor75)', overflow: 'hidden'}}>
                                                    {isImagem ? (
                                                        <img src={img.url} alt={img.nome} style={{width: '100%', height: '100%', objectFit: 'cover'}} />
                                                    ) : <FileText size={40} strokeWidth={1.5} />}
                                                </div>
                                            </a>
                                            <p style={{fontWeight: 700, margin: '0 0 4px 0', fontSize: '14px', wordBreak: 'break-word'}}>{img.nome || "Arquivo"}</p>
                                            <p style={{color: 'var(--TextColor75)', margin: '0 0 8px 0', fontSize: '12px'}}>
                                                {img.created_at ? formatDate(img.created_at) : ""}
                                            </p>
                                            <button
                                                onClick={() => handleDeletarImagem(img.id)}
                                                style={{background: 'var(--DangerBack)', color: 'var(--DangerText)', border: '1px solid var(--DangerText)', borderRadius: '8px', padding: '4px 12px', fontSize: '12px', fontWeight: 600, cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: '4px'}}
                                            >
                                                <X size={13} strokeWidth={2.5} /> Remover
                                            </button>
                                        </div>
                                    );
                                })}
                            </div>
                        )}
                    </div>
                )}

                {/* ABA 4: FINANCEIRO (Feita pela recepção) */}
                {activeTab === "financeiro" && (
                    <div className="forms-section" style={{animation: 'fadeIn 0.3s'}}>
                        <div style={{display: 'grid', gridTemplateColumns: '2fr 1.5fr', gap: '2rem'}}>
                            <div>
                                <h3 style={{color: 'var(--PrimaryColorsTheme)', margin: '0 0 1.5rem 0'}}>Lançar Novo Faturamento</h3>
                                <div style={{background: 'var(--PrimaryColorsBack)', padding: '1.5rem', borderRadius: '16px', border: '1px solid var(--LineColor)'}}>
                                    <div className="field" style={{marginBottom: '1rem'}}>
                                        <label>Procedimento Vinculado</label>
                                        <input
                                            type="text"
                                            placeholder="Ex: Limpeza (Realizada por Dr. Lucas) hoje..."
                                            style={{width: '100%'}}
                                            value={procedimento}
                                            onChange={(e) => setProcedimento(e.target.value)}
                                        />
                                    </div>
                                    <div className="flex-inpus">
                                        <div className="field" style={{margin: 0}}>
                                            <label>Valor Cobrado (R$)</label>
                                            <input
                                                type="number"
                                                placeholder="Ex: 350,00"
                                                style={{width: '100%'}}
                                                value={valorCobranca}
                                                onChange={(e) => setValorCobranca(e.target.value)}
                                            />
                                        </div>
                                        <div className="field" style={{margin: 0}}>
                                            <label>Forma de Pagamento</label>
                                            <select
                                                style={{width: '100%'}}
                                                value={formaPagamento}
                                                onChange={(e) => setFormaPagamento(e.target.value)}
                                            >
                                                <option value="Pix">Pix</option>
                                                <option value="Cartão Crédito">Cartão de Crédito</option>
                                                <option value="Cartão Débito">Cartão de Débito</option>
                                                <option value="Dinheiro">Dinheiro</option>
                                                <option value="Convênio">Convênio</option>
                                            </select>
                                        </div>
                                        <div className="field" style={{margin: 0}}>
                                            <label>Status</label>
                                            <select
                                                style={{width: '100%'}}
                                                value={statusPagamento}
                                                onChange={(e) => setStatusPagamento(e.target.value)}
                                            >
                                                <option value="Pago">Pago</option>
                                                <option value="Pendente">A Receber (Fiado)</option>
                                            </select>
                                        </div>
                                    </div>
                                    {cobrancaErro && (
                                        <p style={{color: 'var(--DangerText)', fontSize: '13px', margin: '1rem 0 0 0'}}>{cobrancaErro}</p>
                                    )}
                                    <button
                                        className="submit"
                                        style={{marginTop: '1.5rem', width: '100%', opacity: salvandoCobranca ? 0.7 : 1}}
                                        onClick={handleSalvarCobranca}
                                        disabled={salvandoCobranca}
                                    >
                                        {salvandoCobranca ? "Salvando..." : "Salvar Cobrança e Atribuir ao Dr."}
                                    </button>
                                </div>
                            </div>

                            <div>
                                <h3 style={{color: 'var(--TextColor)', margin: '0 0 1.5rem 0'}}>Extrato do Paciente</h3>
                                {financeiroLoading ? (
                                    <p style={{color: 'var(--TextColor75)'}}>Carregando extrato...</p>
                                ) : lancamentos.length === 0 ? (
                                    <p style={{color: 'var(--TextColor75)'}}>Nenhum lançamento financeiro para este paciente.</p>
                                ) : (
                                    lancamentos.map((l) => {
                                        const pago = l.status_pagamento === "Pago";
                                        return (
                                            <div key={l.id} style={{borderLeft: `4px solid ${pago ? 'var(--SuccessText)' : 'var(--WarningText)'}`, paddingLeft: '1rem', marginBottom: '1rem'}}>
                                                <p style={{margin: '0 0 4px 0', fontWeight: 700}}>
                                                    {formatCurrency(l.valor)} - {l.status_pagamento || "Pendente"}
                                                    {l.forma_pagamento ? ` via ${l.forma_pagamento}` : ""}
                                                </p>
                                                <p style={{margin: 0, color: 'var(--TextColor75)', fontSize: '13px'}}>
                                                    {l.descricao || "Lançamento"} {l.created_at ? `(${formatDate(l.created_at)})` : ""}
                                                </p>
                                            </div>
                                        );
                                    })
                                )}
                            </div>
                        </div>
                    </div>
                )}
            </main>
        </>
    );
}

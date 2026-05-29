import { useState, useEffect } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { apiCriarPaciente, apiAtualizarPaciente, apiGetPaciente } from "../../services/api";
import { maskCPF, maskPhone, maskCEP, validarCPF, validarTelefone, validarEmail } from "../../utils/formatters";
import Section from "../../components/section/SectionAuth";
import SideBar from "../../components/bar/SideBar";
import { useReceptionSidebar } from "../../hooks/useSidebar";
import { ArrowLeft } from "lucide-react";
import '../../styles/clinic.css';
import '../../styles/Forms.css';

/* MAIN COMPONENT */
function RegisterPatient() {
    const { token } = useAuth();
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();
    const pacienteId = searchParams.get("id");
    const isEditMode = Boolean(pacienteId);

    // Menu da recepção
    const opc_bar = useReceptionSidebar("patients");

    // Controle de Abas
    const [activeTab, setActiveTab] = useState("dados");
    const [isLoading, setIsLoading] = useState(false);

    // Estados Core (Aba 1 e Aba 3)
    const [formData, setFormData] = useState({
        nome: '', cpf: '', rg: '', data_nascimento: '', genero: 'Feminino',
        naturalidade: '', nome_mae: '', profissao: '',
        telefone_whatsapp: '', email: '', emerg_nome: '', emerg_tel: '',
        alergias: '', condicoes: '', medicacoes: '', drogas: '', cirurgias: '',
        peso_kg: '', altura_cm: '', ultima_visita_dentista: '', historia_odontologica: '',
        em_tratamento_medico: false, tratamento_medico_qual: '',
        ja_internado: false, internacao_motivo: '',
        reacao_anestesia: false, reacao_anestesia_qual: ''
    });

    const handleChange = (e) => {
        const { name, value, type, checked } = e.target;
        if (type === "checkbox") {
            setFormData({ ...formData, [name]: checked });
        } else if (name === "cpf") {
            setFormData({ ...formData, cpf: maskCPF(value) });
        } else if (name === "telefone_whatsapp") {
            setFormData({ ...formData, telefone_whatsapp: maskPhone(value) });
        } else if (name === "emerg_tel") {
            setFormData({ ...formData, emerg_tel: maskPhone(value) });
        } else {
            setFormData({ ...formData, [name]: value });
        }
    };

    // Estados de Endereço (Aba 2)
    const [cep, setCep] = useState("");
    const [rua, setRua] = useState("");
    const [bairro, setBairro] = useState("");
    const [cidade, setCidade] = useState("");
    const [estado, setEstado] = useState("");
    const [numero, setNumero] = useState("");

    // EDIÇÃO: carrega e pré-preenche os dados do paciente existente
    useEffect(() => {
        if (!isEditMode) return;

        const carregarPaciente = async () => {
            try {
                const p = await apiGetPaciente(token, pacienteId);
                const end = p.endereco || {};
                const anam = p.anamnese || {};

                setFormData({
                    nome: p.nome || '',
                    cpf: maskCPF(p.cpf || ''),
                    rg: p.rg || '',
                    data_nascimento: p.data_nascimento ? String(p.data_nascimento).slice(0, 10) : '',
                    genero: p.genero || 'Feminino',
                    naturalidade: anam.naturalidade || '',
                    nome_mae: anam.nome_mae || '',
                    profissao: anam.profissao || '',
                    telefone_whatsapp: maskPhone(p.telefone_whatsapp || ''),
                    email: p.email || '',
                    emerg_nome: anam.emergencia_nome || '',
                    emerg_tel: maskPhone(anam.emergencia_telefone || ''),
                    alergias: anam.alergias || '',
                    condicoes: anam.condicoes || '',
                    medicacoes: anam.medicacoes || '',
                    drogas: anam.drogas || '',
                    cirurgias: anam.cirurgias || '',
                    peso_kg: anam.peso_kg ?? '',
                    altura_cm: anam.altura_cm ?? '',
                    ultima_visita_dentista: anam.ultima_visita_dentista || '',
                    historia_odontologica: anam.historia_odontologica || '',
                    em_tratamento_medico: Boolean(anam.em_tratamento_medico),
                    tratamento_medico_qual: anam.tratamento_medico_qual || '',
                    ja_internado: Boolean(anam.ja_internado),
                    internacao_motivo: anam.internacao_motivo || '',
                    reacao_anestesia: Boolean(anam.reacao_anestesia),
                    reacao_anestesia_qual: anam.reacao_anestesia_qual || ''
                });

                setCep(maskCEP(end.cep || ''));
                setRua(end.rua || '');
                setBairro(end.bairro || '');
                setCidade(end.cidade || '');
                setEstado(end.estado || '');
                setNumero(end.numero || '');
            } catch (err) {
                console.error("Erro ao carregar paciente para edição", err);
                alert(`Erro ao carregar paciente: ${err.message}`);
            }
        };

        carregarPaciente();
    }, [isEditMode, pacienteId, token]);

    const buscarCEP = async () => {
        const cepLimpo = cep.replace(/\D/g, '');
        if (cepLimpo.length !== 8) return;
        
        try {
            const response = await fetch(`https://viacep.com.br/ws/${cepLimpo}/json/`);
            const data = await response.json();
            
            if (!data.erro) {
                setRua(data.logradouro);
                setBairro(data.bairro);
                setCidade(data.localidade);
                setEstado(data.uf);
            }
        } catch (error) {
            console.error("Erro ao buscar CEP", error);
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();

        if (!validarCPF(formData.cpf)) {
            alert("CPF inválido.");
            return;
        }
        if (!validarTelefone(formData.telefone_whatsapp)) {
            alert("Telefone / WhatsApp inválido.");
            return;
        }
        if (formData.email && !validarEmail(formData.email)) {
            alert("E-mail inválido.");
            return;
        }

        // Em odonto, anamnese sem alergia/medicação/condição documentada bloqueia
        // anestesia. Backend rejeita; aqui pedimos antes de chegar lá pra dar mensagem clara.
        if (!isEditMode) {
            const faltando = [];
            if (!formData.alergias.trim()) faltando.push("Alergias");
            if (!formData.medicacoes.trim()) faltando.push("Medicações em uso");
            if (!formData.condicoes.trim()) faltando.push("Condições sistêmicas");
            if (faltando.length) {
                alert(
                    `Para cadastrar o paciente é preciso preencher: ${faltando.join(", ")}.\n\n` +
                    `Se não houver, escreva "Nega" ou "Nenhuma".`
                );
                return;
            }
        }

        setIsLoading(true);

        // Montagem avançada de JSON usando a estratégia JSONB combinada com a API Python
        const payload = {
            nome: formData.nome,
            email: formData.email,
            telefone_whatsapp: formData.telefone_whatsapp.replace(/\D/g, ''),
            cpf: formData.cpf.replace(/\D/g, ''),
            rg: formData.rg,
            data_nascimento: formData.data_nascimento,
            genero: formData.genero,
            endereco: {
                cep: cep.replace(/\D/g, ''),
                rua: rua,
                bairro: bairro,
                cidade: cidade,
                estado: estado,
                numero: numero
            },
            anamnese: {
                // Identificação complementar
                naturalidade: formData.naturalidade,
                nome_mae: formData.nome_mae,
                profissao: formData.profissao,
                // Anamnese / saúde
                alergias: formData.alergias,
                condicoes: formData.condicoes,
                medicacoes: formData.medicacoes,
                drogas: formData.drogas,
                cirurgias: formData.cirurgias,
                peso_kg: formData.peso_kg === '' ? null : Number(formData.peso_kg),
                altura_cm: formData.altura_cm === '' ? null : Number(formData.altura_cm),
                ultima_visita_dentista: formData.ultima_visita_dentista,
                historia_odontologica: formData.historia_odontologica,
                em_tratamento_medico: formData.em_tratamento_medico,
                tratamento_medico_qual: formData.em_tratamento_medico ? formData.tratamento_medico_qual : '',
                ja_internado: formData.ja_internado,
                internacao_motivo: formData.ja_internado ? formData.internacao_motivo : '',
                reacao_anestesia: formData.reacao_anestesia,
                reacao_anestesia_qual: formData.reacao_anestesia ? formData.reacao_anestesia_qual : '',
                emergencia_nome: formData.emerg_nome,
                emergencia_telefone: formData.emerg_tel.replace(/\D/g, '')
            }
        };

        try {
            if (isEditMode) {
                await apiAtualizarPaciente(token, pacienteId, payload);
                alert("Alterações salvas com sucesso!");
                navigate(`/reception/patient/view?id=${pacienteId}`);
            } else {
                await apiCriarPaciente(token, payload);
                alert("Paciente cadastrado com sucesso!");
                navigate("/reception/patients");
            }
        } catch (err) {
            alert(`Erro: ${err.message}`);
            console.error(err);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <>
            <Section type_styles="reception" />
            <SideBar opc={opc_bar} styles="reception" />
            
            <main className="mainBar reception register">
                <p>
                    {isEditMode ? (
                        <Link className="text75" to={`/reception/patient/view?id=${pacienteId}`} style={{display: 'inline-flex', alignItems: 'center', gap: '6px'}}>
                            <ArrowLeft size={16} strokeWidth={2} /> Voltar para a Ficha do Paciente
                        </Link>
                    ) : (
                        <Link className="text75" to="/reception/dashboard" style={{display: 'inline-flex', alignItems: 'center', gap: '6px'}}>
                            <ArrowLeft size={16} strokeWidth={2} /> Voltar para o Painel
                        </Link>
                    )}
                </p>

                <div className="camp-clinic camp-register" style={{marginTop: '1rem'}}>
                    <div style={{marginBottom: "2rem"}}>
                        <h1 style={{margin: '0 0 0.5rem 0', color: 'var(--PrimaryColorsTheme)', fontSize: '28px'}}>
                            {isEditMode ? "Editar Paciente" : "Cadastrar Novo Paciente"}
                        </h1>
                        <p className="text75">
                            {isEditMode
                                ? "Atualize a Ficha Clínica e Anamnese. As alterações ficarão salvas no prontuário."
                                : "Preencha a Ficha Clínica e Anamnese. Estes dados ficarão salvos no prontuário."}
                        </p>
                    </div>

                    {/* WIZARD TABS */}
                    <div style={{display: 'flex', gap: '1rem', borderBottom: '1px solid var(--LineColor)', paddingBottom: '1rem', marginBottom: '2rem'}}>
                        <button 
                            type="button"
                            onClick={() => setActiveTab("dados")}
                            style={{background: 'transparent', border: 'none', fontSize: '15px', fontWeight: activeTab === 'dados' ? 800 : 500, color: activeTab === 'dados' ? 'var(--PrimaryColorsTheme)' : 'var(--TextColor75)', cursor: 'pointer', padding: '0 0.5rem'}}
                        >
                            <span style={{background: activeTab === 'dados' ? 'var(--PrimaryColorsTheme)' : 'var(--LineColor)', color: activeTab === 'dados' ? 'white' : 'var(--TextColor75)', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: '22px', height: '22px', borderRadius: '999px', marginRight: '8px', fontSize: '12px', fontWeight: 700}}>1</span>
                            Dados & Contato
                        </button>
                        <button 
                            type="button"
                            onClick={() => setActiveTab("endereco")}
                            style={{background: 'transparent', border: 'none', fontSize: '15px', fontWeight: activeTab === 'endereco' ? 800 : 500, color: activeTab === 'endereco' ? 'var(--PrimaryColorsTheme)' : 'var(--TextColor75)', cursor: 'pointer', padding: '0 0.5rem'}}
                        >
                            <span style={{background: activeTab === 'endereco' ? 'var(--PrimaryColorsTheme)' : 'var(--LineColor)', color: activeTab === 'endereco' ? 'white' : 'var(--TextColor75)', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: '22px', height: '22px', borderRadius: '999px', marginRight: '8px', fontSize: '12px', fontWeight: 700}}>2</span>
                            Endereço
                        </button>
                        <button 
                            type="button"
                            onClick={() => setActiveTab("anamnese")}
                            style={{background: 'transparent', border: 'none', fontSize: '15px', fontWeight: activeTab === 'anamnese' ? 800 : 500, color: activeTab === 'anamnese' ? 'var(--PrimaryColorsTheme)' : 'var(--TextColor75)', cursor: 'pointer', padding: '0 0.5rem'}}
                        >
                            <span style={{background: activeTab === 'anamnese' ? 'var(--PrimaryColorsTheme)' : 'var(--LineColor)', color: activeTab === 'anamnese' ? 'white' : 'var(--TextColor75)', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: '22px', height: '22px', borderRadius: '999px', marginRight: '8px', fontSize: '12px', fontWeight: 700}}>3</span>
                            Anamnese Médica
                        </button>
                    </div>

                    <form onSubmit={handleSubmit}>
                        {/* ABA 1: DADOS BÁSICOS */}
                        {activeTab === "dados" && (
                            <div className="forms-section" style={{animation: 'fadeIn 0.3s'}}>
                                <p className="sec-title" style={{color: 'var(--PrimaryColorsTheme)'}}>Identificação do Paciente</p>
                                
                                <div className="field">
                                    <label>Nome Completo *</label>
                                    <input type="text" name="nome" value={formData.nome} onChange={handleChange} required placeholder="Ex: Maria Fernanda da Silva" />
                                </div>
                                <div className="flex-inpus">
                                    <div className="field">
                                        <label>CPF *</label>
                                        <input type="text" name="cpf" value={formData.cpf} onChange={handleChange} required placeholder="000.000.000-00" />
                                    </div>
                                    <div className="field">
                                        <label>RG</label>
                                        <input type="text" name="rg" value={formData.rg} onChange={handleChange} placeholder="Apenas números (7-9 dígitos)" inputMode="numeric" />
                                    </div>
                                </div>
                                <div className="flex-inpus">
                                    <div className="field">
                                        <label>Data de Nascimento *</label>
                                        <input type="date" name="data_nascimento" value={formData.data_nascimento} onChange={handleChange} required />
                                    </div>
                                    <div className="field">
                                        <label>Gênero *</label>
                                        <select name="genero" value={formData.genero} onChange={handleChange}>
                                            <option>Feminino</option>
                                            <option>Masculino</option>
                                            <option>Outro</option>
                                        </select>
                                    </div>
                                </div>
                                <div className="flex-inpus">
                                    <div className="field">
                                        <label>Naturalidade</label>
                                        <input type="text" name="naturalidade" value={formData.naturalidade} onChange={handleChange} placeholder="Ex: Goiânia - GO" />
                                    </div>
                                    <div className="field">
                                        <label>Profissão</label>
                                        <input type="text" name="profissao" value={formData.profissao} onChange={handleChange} placeholder="Ex: Professora" />
                                    </div>
                                </div>
                                <div className="field">
                                    <label>Nome da Mãe</label>
                                    <input type="text" name="nome_mae" value={formData.nome_mae} onChange={handleChange} placeholder="Ex: Ana Maria da Silva" />
                                </div>

                                <p className="sec-title" style={{marginTop: '2rem', color: 'var(--PrimaryColorsTheme)'}}>Contato & Emergência</p>
                                
                                <div className="flex-inpus">
                                    <div className="field">
                                        <label>Telefone / WhatsApp *</label>
                                        <input type="text" name="telefone_whatsapp" value={formData.telefone_whatsapp} onChange={handleChange} required placeholder="(DD) 90000-0000" />
                                    </div>
                                    <div className="field">
                                        <label>E-mail</label>
                                        <input type="email" name="email" value={formData.email} onChange={handleChange} placeholder="paciente@email.com" />
                                    </div>
                                </div>
                                <div className="flex-inpus">
                                    <div className="field">
                                        <label>Nome do Contato de Emergência</label>
                                        <input type="text" name="emerg_nome" value={formData.emerg_nome} onChange={handleChange} placeholder="Ex: João da Silva" />
                                    </div>
                                    <div className="field">
                                        <label>Telefone de Emergência</label>
                                        <input type="text" name="emerg_tel" value={formData.emerg_tel} onChange={handleChange} placeholder="(DD) 90000-0000" />
                                    </div>
                                </div>

                                <div style={{ display: "flex", justifyContent: "flex-end", marginTop: '2rem' }}>
                                    <button type="button" className="submit" onClick={() => setActiveTab("endereco")}>Avançar para Endereço</button>
                                </div>
                            </div>
                        )}

                        {/* ABA 2: ENDEREÇO */}
                        {activeTab === "endereco" && (
                            <div className="forms-section" style={{animation: 'fadeIn 0.3s'}}>
                                <p className="sec-title" style={{color: 'var(--PrimaryColorsTheme)', margin: 0}}>Endereço Residencial</p>
                                <p className="text75" style={{fontSize: '13px', margin: '4px 0 1.5rem 0'}}>Digite o CEP para buscar automaticamente.</p>

                                <div className="flex-inpus">
                                    <div className="field">
                                        <label>CEP *</label>
                                        <input type="text" placeholder="00000-000" value={cep} onChange={(e) => setCep(maskCEP(e.target.value))} onBlur={buscarCEP} />
                                    </div>
                                    <div className="field">
                                        <label>Estado (UF)</label>
                                        <input type="text" value={estado} onChange={e => setEstado(e.target.value)} placeholder="Ex: SP" />
                                    </div>
                                </div>

                                <div className="flex-inpus">
                                    <div className="field">
                                        <label>Cidade</label>
                                        <input type="text" value={cidade} onChange={e => setCidade(e.target.value)} placeholder="Ex: São Paulo" />
                                    </div>
                                    <div className="field">
                                        <label>Bairro</label>
                                        <input type="text" value={bairro} onChange={e => setBairro(e.target.value)} placeholder="Centro" />
                                    </div>
                                </div>

                                <div className="flex-inpus">
                                    <div className="field" style={{flex: 2}}>
                                        <label>Endereço (Rua/Avenida)</label>
                                        <input type="text" value={rua} onChange={e => setRua(e.target.value)} placeholder="Rua das Flores" />
                                    </div>
                                    <div className="field">
                                        <label>Número</label>
                                        <input type="text" value={numero} onChange={e => setNumero(e.target.value)} placeholder="123" />
                                    </div>
                                </div>

                                <div style={{ display: "flex", justifyContent: "space-between", marginTop: '2rem' }}>
                                    <button type="button" className="submit" style={{background: 'var(--BackColor)', color: 'var(--TextColor)', border: '1px solid var(--LineColor)', boxShadow:'none'}} onClick={() => setActiveTab("dados")}>Voltar</button>
                                    <button type="button" className="submit" onClick={() => setActiveTab("anamnese")}>Avançar para Anamnese</button>
                                </div>
                            </div>
                        )}

                        {/* ABA 3: ANAMNESE E SUBMIT */}
                        {activeTab === "anamnese" && (
                            <div className="forms-section" style={{animation: 'fadeIn 0.3s'}}>
                                <p className="sec-title" style={{color: 'var(--PrimaryColorsTheme)'}}>Anamnese e Saúde Geral (Prontuário)</p>
                                <p className="text75" style={{fontSize: '13px', marginBottom: '1.5rem'}}>Este é o prontuário eletrônico. Mantenha os dados atualizados.</p>

                                <div className="field">
                                    <label>Alergias Conhecidas *</label>
                                    <textarea name="alergias" value={formData.alergias} onChange={handleChange} required placeholder='Ex: Penicilina, Iodo, Látex... Se não houver, escreva "Nega".' rows="3"></textarea>
                                </div>

                                <div className="field">
                                    <label>Condições Sistêmicas *</label>
                                    <textarea name="condicoes" value={formData.condicoes} onChange={handleChange} required placeholder='Ex: Hipertensão, Diabetes, gestante... Se não houver, escreva "Nenhuma".' rows="3"></textarea>
                                </div>

                                <div className="field">
                                    <label>Medicações em uso contínuo *</label>
                                    <textarea name="medicacoes" value={formData.medicacoes} onChange={handleChange} required placeholder='Liste os remédios que o paciente toma. Se não tomar, escreva "Nenhuma".' rows="3"></textarea>
                                </div>

                                <div className="field">
                                    <label>Uso de drogas lícitas e ilícitas</label>
                                    <textarea name="drogas" value={formData.drogas} onChange={handleChange} placeholder="Álcool, tabagismo, outros..." rows="3"></textarea>
                                </div>

                                <div className="field">
                                    <label>Cirurgias prévias e problemas de cicatrização/sangramento</label>
                                    <textarea name="cirurgias" value={formData.cirurgias} onChange={handleChange} placeholder="Alguma cirurgia recente ou problemas de coagulação?" rows="3"></textarea>
                                </div>

                                <div className="flex-inpus">
                                    <div className="field">
                                        <label>Peso (kg)</label>
                                        <input type="number" name="peso_kg" value={formData.peso_kg} onChange={handleChange} placeholder="Ex: 72" min="0" step="0.1" inputMode="decimal" />
                                    </div>
                                    <div className="field">
                                        <label>Altura (cm)</label>
                                        <input type="number" name="altura_cm" value={formData.altura_cm} onChange={handleChange} placeholder="Ex: 168" min="0" step="1" inputMode="numeric" />
                                    </div>
                                </div>

                                <div className="field">
                                    <label>Última visita ao dentista</label>
                                    <select name="ultima_visita_dentista" value={formData.ultima_visita_dentista} onChange={handleChange}>
                                        <option value="">Selecione...</option>
                                        <option value="Menos de 6 meses">Menos de 6 meses</option>
                                        <option value="6 meses a 1 ano">6 meses a 1 ano</option>
                                        <option value="1 a 2 anos">1 a 2 anos</option>
                                        <option value="Mais de 2 anos">Mais de 2 anos</option>
                                        <option value="Nunca">Nunca foi ao dentista</option>
                                    </select>
                                </div>

                                <div className="field">
                                    <label>História odontológica (tratamentos anteriores)</label>
                                    <textarea name="historia_odontologica" value={formData.historia_odontologica} onChange={handleChange} placeholder="Ex: aparelho ortodôntico, canais, extrações, próteses, experiências traumáticas..." rows="3"></textarea>
                                </div>

                                <label style={{display: 'flex', alignItems: 'center', gap: '10px', padding: '12px 0', cursor: 'pointer'}}>
                                    <input type="checkbox" name="em_tratamento_medico" checked={formData.em_tratamento_medico} onChange={handleChange} style={{width: '18px', height: '18px', cursor: 'pointer'}} />
                                    <span style={{fontWeight: 600, fontSize: '15px'}}>Está em tratamento médico atualmente?</span>
                                </label>
                                {formData.em_tratamento_medico && (
                                    <div className="field">
                                        <label>Qual tratamento?</label>
                                        <input type="text" name="tratamento_medico_qual" value={formData.tratamento_medico_qual} onChange={handleChange} placeholder="Descreva o tratamento médico em curso" />
                                    </div>
                                )}

                                <label style={{display: 'flex', alignItems: 'center', gap: '10px', padding: '12px 0', cursor: 'pointer'}}>
                                    <input type="checkbox" name="ja_internado" checked={formData.ja_internado} onChange={handleChange} style={{width: '18px', height: '18px', cursor: 'pointer'}} />
                                    <span style={{fontWeight: 600, fontSize: '15px'}}>Já foi internado(a)?</span>
                                </label>
                                {formData.ja_internado && (
                                    <div className="field">
                                        <label>Motivo da internação</label>
                                        <input type="text" name="internacao_motivo" value={formData.internacao_motivo} onChange={handleChange} placeholder="Motivo e quando ocorreu" />
                                    </div>
                                )}

                                <label style={{display: 'flex', alignItems: 'center', gap: '10px', padding: '12px 0', cursor: 'pointer'}}>
                                    <input type="checkbox" name="reacao_anestesia" checked={formData.reacao_anestesia} onChange={handleChange} style={{width: '18px', height: '18px', cursor: 'pointer'}} />
                                    <span style={{fontWeight: 600, fontSize: '15px'}}>Já teve alguma reação à anestesia odontológica?</span>
                                </label>
                                {formData.reacao_anestesia && (
                                    <div className="field">
                                        <label>Qual reação?</label>
                                        <input type="text" name="reacao_anestesia_qual" value={formData.reacao_anestesia_qual} onChange={handleChange} placeholder="Ex: taquicardia, desmaio, alergia, edema..." />
                                        <p style={{fontSize: '12px', color: 'var(--TextColor75)', margin: '6px 0 0 0'}}>
                                            Diferencie alergia verdadeira de reações como taquicardia/desmaio pela epinefrina.
                                        </p>
                                    </div>
                                )}

                                <div style={{ display: "flex", justifyContent: "space-between", marginTop: '2rem' }}>
                                    <button type="button" className="submit" style={{background: 'var(--BackColor)', color: 'var(--TextColor)', border: '1px solid var(--LineColor)', boxShadow:'none'}} onClick={() => setActiveTab("endereco")}>Voltar</button>
                                    <button type="submit" disabled={isLoading} className="submit" style={{background: 'var(--PrimaryColorsTheme)', boxShadow: 'none'}}>
                                        {isLoading
                                            ? "Salvando..."
                                            : isEditMode ? "Salvar Alterações" : "Finalizar Cadastro do Paciente"}
                                    </button>
                                </div>
                            </div>
                        )}
                    </form>
                </div>
            </main>
        </>
    );
}

export default RegisterPatient;

import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { apiCreateClinic } from "../../services/api";
import { maskCNPJ, maskPhone, validarCNPJ } from "../../utils/formatters";
import Section from "../../components/section/SectionAuth"
import SideBar from "../../components/bar/SideBar"
import { useOwnerSidebar } from "../../hooks/useSidebar";
import { ArrowLeft } from "lucide-react";
import '../../styles/clinic.css';
import '../../styles/Forms.css';

/* MAIN COMPONENT */
function RegisterClinic() {
    const { token } = useAuth();
    const navigate = useNavigate();
    
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");

    const [name_clinic, setNameClinic] = useState("");
    const [CNPJ, setCNPJ] = useState("");
    const [razao_social, setRazaoSocial] = useState("");
    const [resumo, setResumo] = useState("");

    const [whatsapp, setWhatsapp] = useState("");
    const [telefone, setTelefone] = useState("");
    const [instagram, setInstagram] = useState("");
    const [facebook, setFacebook] = useState("");

    const [pais, setPais] = useState("");
    const [estado, setEstado] = useState("");
    const [cidade, setCidade] = useState("");
    const [endereco, setEndereco] = useState("");

    const opc_bar = useOwnerSidebar("clinic");

    async function handleSubmit(e) {
        e.preventDefault();
        setError("");

        if (CNPJ && !validarCNPJ(CNPJ)) {
            setError("CNPJ inválido.");
            return;
        }

        setLoading(true);

        const newClinic = {
            nome: name_clinic,
            nome_fantasia: name_clinic,
            cnpj: CNPJ.replace(/\D/g, ""),
            telefone: telefone.replace(/\D/g, ""),
            endereco: {
                logradouro: endereco,
                cidade: cidade,
                estado: estado,
                pais: pais,
            },
        };

        try {
            const clinic = await apiCreateClinic(token, newClinic);
            alert("Clínica registrada com sucesso!");
            navigate(`/owner/clinic/`);
        } catch (err) {
            setError(err.message || "Erro ao registrar clínica.");
            alert(err.message || "Erro ao registrar clínica.");
        } finally {
            setLoading(false);
        }
    }

    return (
        <>
            <Section type_styles="owner" />
            <SideBar opc={opc_bar} styles="owner" />
            
            <main className="mainBar owner register">
                <p>
                    <Link className="text75" to="/owner/clinic" style={{ display: "inline-flex", alignItems: "center", gap: "6px" }}>
                        <ArrowLeft size={16} strokeWidth={2} /> Voltar para Minhas Clínicas
                    </Link>
                </p>
                <div className="camp-clinic camp-register">
                    <div>
                        <h1 style={{margin: '0 0 0.5rem 0'}}>Configurações da Clínica</h1>
                        <p className="text75">Preencha os dados abaixo para estruturar a presença da sua clínica no sistema.</p>

                        <form onSubmit={handleSubmit} style={{marginTop: '2rem'}}>

                            <div className="forms-section">
                                <p className="sec-title">Dados Básicos</p>
                                
                                <div className="field">
                                    <label htmlFor="name_clinic">Nome da Clínica *</label>
                                    <input
                                        id="name_clinic"
                                        type="text"
                                        value={name_clinic}
                                        onChange={(e) => setNameClinic(e.target.value)}
                                    />
                                </div>
                                
                                <div className="flex-inpus">
                                    <div className="field">
                                        <label htmlFor="CNPJ">CNPJ *</label>
                                        <input
                                            id="CNPJ"
                                            type="text"
                                            value={CNPJ}
                                            onChange={(e) => setCNPJ(maskCNPJ(e.target.value))}
                                        />
                                    </div>
                                    
                                    <div className="field">
                                        <label htmlFor="razao_social">Razão Social</label>
                                        <input
                                            id="razao_social"
                                            type="text"
                                            value={razao_social}
                                            onChange={(e) => setRazaoSocial(e.target.value)}
                                        />
                                    </div>
                                </div>
                                
                                <div className="field">
                                    <label htmlFor="resumo">Resumo da Clínica</label>
                                    <textarea
                                        id="resumo"
                                        type="text"
                                        value={resumo}
                                        onChange={(e) => setResumo(e.target.value)}
                                    />
                                </div>
                            </div>

                            <div className="forms-section">
                                <p className="sec-title">Redes Sociais</p>
                                
                                <div className="flex-inpus">
                                    <div className="field">
                                        <label htmlFor="whatsapp">Whatsapp da Clínica *</label>
                                        <input
                                            id="whatsapp"
                                            type="text"
                                            value={whatsapp}
                                            onChange={(e) => setWhatsapp(maskPhone(e.target.value))}
                                        />
                                    </div>
                                    
                                    <div className="field">
                                        <label htmlFor="telefone">Telefone da Clínica</label>
                                        <input
                                            id="telefone"
                                            type="text"
                                            value={telefone}
                                            onChange={(e) => setTelefone(maskPhone(e.target.value))}
                                        />
                                    </div>
                                </div>
                                
                                <div className="flex-inpus">
                                    <div className="field">
                                        <label htmlFor="instagram">Instagram da Clínica</label>
                                        <input
                                            id="instagram"
                                            type="text"
                                            value={instagram}
                                            onChange={(e) => setInstagram(e.target.value)}
                                        />
                                    </div>
                                    
                                    <div className="field">
                                        <label htmlFor="facebook">Facebook da Clínica</label>
                                        <input
                                            id="facebook"
                                            type="text"
                                            value={facebook}
                                            onChange={(e) => setFacebook(e.target.value)}
                                        />
                                    </div>
                                </div>
                            </div>

                            <div className="forms-section">
                                <p className="sec-title">Endereço</p>

                                <div className="field">
                                    <label htmlFor="pais">País</label>
                                    <input
                                        id="pais"
                                        type="text"
                                        value={pais}
                                        onChange={(e) => setPais(e.target.value)}
                                    />
                                </div>
                                
                                <div className="flex-inpus">
                                    <div className="field">
                                        <label htmlFor="estado">Estado</label>
                                        <input
                                            id="estado"
                                            type="text"
                                            value={estado}
                                            onChange={(e) => setEstado(e.target.value)}
                                        />
                                    </div>
                                    
                                    <div className="field">
                                        <label htmlFor="cidade">Cidade</label>
                                        <input
                                            id="cidade"
                                            type="text"
                                            value={cidade}
                                            onChange={(e) => setCidade(e.target.value)}
                                        />
                                    </div>
                                </div>

                                <div className="field">
                                    <label htmlFor="endereco">Endereço Completo</label>
                                    <input
                                        id="endereco"
                                        type="text"
                                        value={endereco}
                                        onChange={(e) => setEndereco(e.target.value)}
                                    />
                                </div>
                            </div>
                            
                            <div style={{ display: "flex", justifyContent: "end", marginTop: '2rem' }}>
                                <button
                                    type="submit"
                                    className="submit"
                                    disabled={loading}
                                >
                                    {loading ? "Salvando..." : "Salvar Configurações"}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            </main>
        </>
    );
}

/* STANDARD EXPORT */
export default RegisterClinic;

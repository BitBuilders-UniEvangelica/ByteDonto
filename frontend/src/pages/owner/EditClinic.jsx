/* IMPORTS OF COMPONENTS */
import { useState, useEffect } from "react";
import { Link, useParams, Navigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { apiGetClinic, apiUpdateClinic } from "../../services/api";
import { maskCNPJ, maskPhone, validarCNPJ } from "../../utils/formatters";
import Section from "../../components/section/SectionAuth";
import SideBar from "../../components/bar/SideBar";
import { useOwnerSidebar } from "../../hooks/useSidebar";
import { ArrowLeft } from "lucide-react";
import '../../styles/clinic.css';
import '../../styles/Forms.css';

/* MAIN COMPONENT */
function EditClinic() {
    const { id } = useParams();
    const { token } = useAuth();
    
    /* STATES */
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    
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

    /* LOAD DATA FROM API */
    useEffect(() => {
        if (id && token) {
            apiGetClinic(token, id)
                .then((clinicData) => {
                    setNameClinic(clinicData.nome || clinicData.nome_fantasia || "");
                    setCNPJ(maskCNPJ(clinicData.cnpj || ""));
                    setRazaoSocial(clinicData.razao_social || "");
                    setResumo(clinicData.resumo || "");

                    setWhatsapp(maskPhone(clinicData.telefone || ""));
                    setTelefone(maskPhone(clinicData.telefone || ""));
                    setInstagram(clinicData.instagram || "");
                    setFacebook(clinicData.facebook || "");

                    setPais(clinicData.endereco?.pais || "");
                    setEstado(clinicData.endereco?.estado || "");
                    setCidade(clinicData.endereco?.cidade || "");
                    setEndereco(clinicData.endereco?.logradouro || "");
                })
                .catch((e) => {
                    console.error("Erro ao carregar clínica", e);
                    alert("Não foi possível carregar os dados.");
                })
                .finally(() => setLoading(false));
        }
    }, [id, token]);

    /* SUBMIT */
    async function handleSubmit(e) {
        e.preventDefault();

        if (CNPJ && !validarCNPJ(CNPJ)) {
            alert("CNPJ inválido.");
            return;
        }

        setSaving(true);

        const updatedClinic = {
            nome: name_clinic,
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
            await apiUpdateClinic(token, id, updatedClinic);
            alert("Dados da clínica salvos com sucesso no banco principal!");
        } catch (e) {
            console.error(e);
            alert("Falha ao salvar: " + e.message);
        } finally {
            setSaving(false);
        }
    }

    if (loading) return <div style={{padding: '50px', textAlign: 'center'}}>Carregando os dados...</div>;

    return (
        <>
            <Section type_styles="owner" />
            <SideBar opc={opc_bar} styles="owner" />
            
            <main className="mainBar owner register">
                <p>
                    <Link className="text75" to={`/owner/view-clinic/${id}`} style={{ display: "inline-flex", alignItems: "center", gap: "6px" }}>
                        <ArrowLeft size={16} strokeWidth={2} /> Voltar para Visão Geral
                    </Link>
                </p>

                <div className="camp-clinic camp-register">
                    <div>
                        <h1 style={{margin: '0 0 0.5rem 0'}}>Atualizar Clínica</h1>
                        <p className="text75">
                            Mantenha os dados de sua clínica sempre atualizados para melhor gestão.
                        </p>

                        <form onSubmit={handleSubmit} style={{marginTop: '2rem'}}>

                            {/* DADOS BÁSICOS */}
                            <div className="forms-section">
                                <p className="sec-title">Dados Básicos</p>
                                
                                <div className="field">
                                    <label>Nome da Clínica *</label>
                                    <input
                                        type="text"
                                        value={name_clinic}
                                        onChange={(e) => setNameClinic(e.target.value)}
                                    />
                                </div>
                                
                                <div className="flex-inpus">
                                    <div className="field">
                                        <label>CNPJ *</label>
                                        <input
                                            type="text"
                                            value={CNPJ}
                                            onChange={(e) => setCNPJ(maskCNPJ(e.target.value))}
                                        />
                                    </div>
                                    
                                    <div className="field">
                                        <label>Razão Social</label>
                                        <input
                                            type="text"
                                            value={razao_social}
                                            onChange={(e) => setRazaoSocial(e.target.value)}
                                        />
                                    </div>
                                </div>
                                
                                <div className="field">
                                    <label>Resumo da Clínica</label>
                                    <textarea
                                        value={resumo}
                                        onChange={(e) => setResumo(e.target.value)}
                                    />
                                </div>
                            </div>

                            {/* REDES SOCIAIS */}
                            <div className="forms-section">
                                <p className="sec-title">Redes Sociais</p>
                                
                                <div className="flex-inpus">
                                    <div className="field">
                                        <label>Whatsapp *</label>
                                        <input
                                            type="text"
                                            value={whatsapp}
                                            onChange={(e) => setWhatsapp(maskPhone(e.target.value))}
                                        />
                                    </div>
                                    
                                    <div className="field">
                                        <label>Telefone</label>
                                        <input
                                            type="text"
                                            value={telefone}
                                            onChange={(e) => setTelefone(maskPhone(e.target.value))}
                                        />
                                    </div>
                                </div>
                                
                                <div className="flex-inpus">
                                    <div className="field">
                                        <label>Instagram</label>
                                        <input
                                            type="text"
                                            value={instagram}
                                            onChange={(e) => setInstagram(e.target.value)}
                                        />
                                    </div>
                                    
                                    <div className="field">
                                        <label>Facebook</label>
                                        <input
                                            type="text"
                                            value={facebook}
                                            onChange={(e) => setFacebook(e.target.value)}
                                        />
                                    </div>
                                </div>
                            </div>

                            {/* ENDEREÇO */}
                            <div className="forms-section">
                                <p className="sec-title">Endereço</p>

                                <div className="field">
                                    <label>País</label>
                                    <input
                                        type="text"
                                        value={pais}
                                        onChange={(e) => setPais(e.target.value)}
                                    />
                                </div>
                                
                                <div className="flex-inpus">
                                    <div className="field">
                                        <label>Estado</label>
                                        <input
                                            type="text"
                                            value={estado}
                                            onChange={(e) => setEstado(e.target.value)}
                                        />
                                    </div>
                                    
                                    <div className="field">
                                        <label>Cidade</label>
                                        <input
                                            type="text"
                                            value={cidade}
                                            onChange={(e) => setCidade(e.target.value)}
                                        />
                                    </div>
                                </div>

                                <div className="field">
                                    <label>Endereço Completo</label>
                                    <input
                                        type="text"
                                        value={endereco}
                                        onChange={(e) => setEndereco(e.target.value)}
                                    />
                                </div>
                            </div>
                            
                            <div style={{ display: "flex", justifyContent: "end", marginTop: '2rem' }}>
                                <button type="submit" className="submit" disabled={saving}>
                                    {saving ? "Salvando..." : "Salvar Atualizações"}
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
export default EditClinic;
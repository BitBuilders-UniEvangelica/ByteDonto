import { useState, useEffect } from "react";
import { Link, useParams, useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { apiGetClinic, apiGetMetricas } from "../../services/api";
import { formatCNPJ, formatPhone } from "../../utils/formatters";
import Section from "../../components/section/SectionAuth";
import SideBar from "../../components/bar/SideBar";
import Card from "../../components/card/CardInfo";
import IMG from "../../assets/img/icon01.png";
import { useOwnerSidebar } from "../../hooks/useSidebar";
import ButtonP from "../../components/buttons/ButtonsRediText";
import { ArrowLeft } from "lucide-react";
import '../../styles/clinic.css';

function ViewClinic() {
    const { id } = useParams();
    const { token } = useAuth();
    const navigate = useNavigate();

    const [clinica, setClinica] = useState(null);
    const [metricas, setMetricas] = useState(null);
    const [loading, setLoading] = useState(true);

    const opc_bar = useOwnerSidebar("clinic");

    useEffect(() => {
        apiGetClinic(token, id)
            .then(data => setClinica(data))
            .catch(() => navigate("/owner/clinic"))
            .finally(() => setLoading(false));
    }, [id, token]);

    // Métricas da clínica VISUALIZADA (passa o id), não da clínica ativa.
    useEffect(() => {
        apiGetMetricas(token, id)
            .then(m => setMetricas(m))
            .catch(() => setMetricas(null));
    }, [token, id]);

    const totalConsultas = metricas?.total_consultas ?? 0;
    const consultasFinalizadas = metricas?.consultas_finalizadas ?? 0;

    if (loading) {
        return (
            <>
                <Section type_styles="owner" />
                <SideBar opc={opc_bar} styles="owner" />
                <main className="mainBar owner"><p className="text75">Carregando clínica...</p></main>
            </>
        );
    }

    if (!clinica) return null;

    return (
        <>
            <Section type_styles="owner" />
            <SideBar opc={opc_bar} styles="owner" />

            <main className="mainBar owner">
                <Link className="view-back-link text75" to="/owner/clinic" style={{ display: "inline-flex", alignItems: "center", gap: "6px" }}>
                    <ArrowLeft size={16} strokeWidth={2} /> Voltar para Minhas Clínicas
                </Link>

                <div className="view-header">
                    <div className="circle">
                        <img src={clinica.logo || IMG} alt="Logo" />
                    </div>
                    <div className="text">
                        <h1>{clinica.nome || clinica.nome_fantasia}</h1>
                        <p>{formatCNPJ(clinica.cnpj)} | {formatPhone(clinica.telefone)}</p>
                        <Link to={`/owner/edit-clinic/${id}`}>Editar Informações da Clínica</Link>
                    </div>
                </div>

                <div className="camp-clinic camp-view">
                    <div>
                        <h2>Informações Gerais</h2>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginTop: '1rem' }}>
                            <p className="text75" style={{ margin: 0 }}>Visão geral</p>
                        </div>
                        <div className="cards">
                            <Card title="Nº Pacientes Cadastrados" date={String(metricas?.total_pacientes ?? 0)} />
                            <Card title="Nº Consultas Cadastradas" date={String(totalConsultas)} />
                            <Card title="Nº de Consultas Finalizadas" date={String(consultasFinalizadas)} />
                        </div>
                    </div>

                    <div style={{ marginTop: '1rem' }}>
                        <h2>Membros da Equipe</h2>
                        <div className="cards">
                            <Card title="Nº Total de Membros" date={String(metricas?.total_membros ?? 0)} />
                            <Card title="Nº de Especialistas Ativos" date={String(metricas?.total_especialistas ?? 0)} />
                            <Card title="Nº de Consultas Hoje" date={String(metricas?.consultas_hoje ?? 0)} />
                        </div>
                        <div style={{ width: "100%", display: "flex", justifyContent: "flex-end", marginTop: "2rem" }}>
                            <ButtonP text={"Gerenciar Equipe"} url={`/owner/bind-clinic/${id}`} />
                        </div>
                    </div>
                </div>
            </main>
        </>
    );
}

export default ViewClinic;

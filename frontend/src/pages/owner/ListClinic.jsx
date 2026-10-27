import { useState, useEffect, useLayoutEffect, useRef } from "react";
import { useAuth } from "../../context/AuthContext";
import { apiGetClinics, apiGetMetricas, apiAtivarClinica } from "../../services/api";
import Section from "../../components/section/SectionAuth";
import ButtonH1 from "../../components/buttons/ButtonsRediTitle";
import SideBar from "../../components/bar/SideBar";
import CampNotList from "../../components/camp/NotList";
import CampList from "../../components/camp/ListClinic";
import { useOwnerSidebar } from "../../hooks/useSidebar";
import { Users, CalendarDays, Wallet, Stethoscope } from "lucide-react";
import ToothIcon from "../../components/icons/ToothIcon";
import IMG from "../../assets/img/icon01.png";
import '../../styles/clinic.css';
import '../../styles/Input.css';

const METRICAS_CONFIG = [
    { key: "total_pacientes",    label: "Total de Pacientes",  Icon: Users,       moeda: false },
    { key: "consultas_hoje",     label: "Consultas Hoje",      Icon: CalendarDays,moeda: false },
    { key: "total_especialistas",label: "Especialistas",       Icon: ToothIcon,   moeda: false },
    { key: "receita_mes",        label: "Receita do Mês",      Icon: Wallet,      moeda: true  },
    { key: "total_membros",      label: "Membros da Equipe",   Icon: Stethoscope, moeda: false },
];

// Níveis de layout dos cards de métricas, aplicados em sequência sempre que
// o grid estoura a largura disponível (scroll horizontal):
// 0 → 5 cards em 1 linha
// 1 → remove "Especialistas", 4 cards em 1 linha
// 2 → 4 cards em 2 colunas
// 3 → 4 cards em 1 coluna, sem o quadrado do ícone
const NIVEIS_METRICAS = [
    { colunas: 5, semEspecialistas: false, comIcone: true  },
    { colunas: 4, semEspecialistas: true,  comIcone: true  },
    { colunas: 2, semEspecialistas: true,  comIcone: true  },
    { colunas: 1, semEspecialistas: true,  comIcone: false },
];

const cardStyle = { background: "var(--ThemeColor)", borderRadius: "14px", border: "1px solid var(--LineColor)", padding: "22px", boxShadow: "var(--shadow-sm)" };

function MetricaSkeleton({ comIcone }) {
    return (
        <div style={cardStyle}>
            {comIcone && <div style={{ width: "40px", height: "40px", borderRadius: "10px", background: "var(--LineColor)", marginBottom: "1rem" }} />}
            <div style={{ width: "60%", height: "32px", borderRadius: "8px", background: "var(--LineColor)", marginBottom: "0.5rem" }} />
            <div style={{ width: "80%", height: "14px", borderRadius: "6px", background: "var(--LineColor)" }} />
        </div>
    );
}

function ListClinic() {
    const { token, refreshUser } = useAuth();
    const [clinicas, setClinicas] = useState([]);
    const [busca, setBusca] = useState("");
    const [loading, setLoading] = useState(true);
    const [metricas, setMetricas] = useState(null);
    const [loadingMetricas, setLoadingMetricas] = useState(true);
    const [ativandoId, setAtivandoId] = useState(null);

    const opc_bar = useOwnerSidebar("clinic");

    // ---- Responsividade dos cards de métricas ----
    const gridMetricasRef = useRef(null);
    const [nivelMetricas, setNivelMetricas] = useState(0);
    const [larguraMetricas, setLarguraMetricas] = useState(0);

    // Quando a largura muda, volta ao layout completo e reavalia do zero.
    useEffect(() => {
        const el = gridMetricasRef.current;
        if (!el) return;
        let ultimaLargura = el.clientWidth;
        const observer = new ResizeObserver(() => {
            const largura = el.clientWidth;
            if (largura === ultimaLargura) return;
            ultimaLargura = largura;
            setNivelMetricas(0);
            setLarguraMetricas(largura);
        });
        observer.observe(el);
        return () => observer.disconnect();
    }, []);

    // Antes de pintar: se o grid estourou a largura, avança para o próximo nível.
    useLayoutEffect(() => {
        const el = gridMetricasRef.current;
        if (!el) return;
        if (el.scrollWidth > el.clientWidth + 1 && nivelMetricas < NIVEIS_METRICAS.length - 1) {
            setNivelMetricas(n => n + 1);
        }
    }, [nivelMetricas, larguraMetricas, loadingMetricas, metricas]);

    const layoutMetricas = NIVEIS_METRICAS[nivelMetricas];
    const metricasVisiveis = layoutMetricas.semEspecialistas
        ? METRICAS_CONFIG.filter(m => m.key !== "total_especialistas")
        : METRICAS_CONFIG;

    function carregarClinicas() {
        return apiGetClinics(token)
            .then(data => setClinicas(Array.isArray(data) ? data : []))
            .catch(err => console.error("Erro ao carregar clínicas", err));
    }

    function carregarMetricas() {
        return apiGetMetricas(token)
            .then(data => setMetricas(data))
            .catch(err => console.error("Erro ao carregar métricas", err));
    }

    useEffect(() => {
        carregarClinicas().finally(() => setLoading(false));
    }, [token]);

    useEffect(() => {
        if (!token) return;
        carregarMetricas().finally(() => setLoadingMetricas(false));
    }, [token]);

    async function handleAtivar(clinicaId) {
        setAtivandoId(clinicaId);
        try {
            await apiAtivarClinica(token, clinicaId);
            // Atualiza o perfil (clinica_id ativa) e recarrega listas/métricas,
            // que passam a refletir a clínica recém-selecionada.
            await refreshUser();
            await Promise.all([carregarClinicas(), carregarMetricas()]);
        } catch (err) {
            console.error("Erro ao trocar de clínica", err);
        } finally {
            setAtivandoId(null);
        }
    }

    const clinicasFiltradas = clinicas.filter(c =>
        (c.nome || c.nome_fantasia)?.toLowerCase().includes(busca.toLowerCase()) ||
        c.cnpj?.includes(busca)
    );

    return (
        <>
            <Section type_styles="owner" />
            <SideBar opc={opc_bar} styles="owner" />
            <main className="mainBar owner">

                {/* ---- MÉTRICAS DO DONO ---- */}
                <div
                    ref={gridMetricasRef}
                    style={{ display: "grid", gridTemplateColumns: `repeat(${layoutMetricas.colunas}, 1fr)`, gap: "1rem", marginBottom: "1.5rem", minWidth: 0 }}
                >
                    {metricasVisiveis.map((m) => {
                        if (loadingMetricas) {
                            return <MetricaSkeleton key={m.key} comIcone={layoutMetricas.comIcone} />;
                        }
                        const valor = metricas ? metricas[m.key] : null;
                        const display = valor == null
                            ? "—"
                            : m.moeda
                                ? Number(valor).toLocaleString("pt-BR", { style: "currency", currency: "BRL" })
                                : valor;
                        const Icon = m.Icon;
                        return (
                            <div key={m.key} style={cardStyle}>
                                {layoutMetricas.comIcone && (
                                    <div style={{ width: "40px", height: "40px", borderRadius: "10px", background: "var(--PrimaryColorsBack)", color: "var(--PrimaryColorsTheme)", display: "flex", alignItems: "center", justifyContent: "center", marginBottom: "1rem" }}>
                                        <Icon size={20} strokeWidth={2} />
                                    </div>
                                )}
                                <p style={{ margin: "0 0 0.25rem 0", fontSize: "28px", fontWeight: 800, color: "var(--TextColor)", fontFamily: "var(--font-secondary)", lineHeight: 1, whiteSpace: "nowrap" }}>{display}</p>
                                <p style={{ margin: 0, fontSize: "13px", color: "var(--TextColor75)", fontWeight: 600, whiteSpace: "nowrap" }}>{m.label}</p>
                            </div>
                        );
                    })}
                </div>
                {/* ---- FIM MÉTRICAS ---- */}

                <div style={{ display: "flex", justifyContent: "space-between", alignItems: 'center' }}>
                    <div>
                        <h1 style={{ margin: 0, fontSize: '26px', color: 'var(--TextColor)' }}>Minhas Clínicas</h1>
                        <p className="text75">Gerencie as clínicas cadastradas em sua conta</p>
                    </div>
                    <ButtonH1 text={"Registrar Nova Clínica"} url="/owner/clinic/register" />
                </div>
                <div style={{ marginTop: '1rem' }}>
                    <input
                        type="text"
                        placeholder="Buscar clínica por nome ou CNPJ..."
                        value={busca}
                        onChange={e => setBusca(e.target.value)}
                        style={{ padding: '14px 16px', borderRadius: '12px', border: '1px solid var(--LineColor)', width: '100%', maxWidth: '400px' }}
                    />
                </div>
                <div className="camp-clinic camp-list" style={{ marginTop: '1rem' }}>
                    <h2 style={{ margin: '0 0 1rem 0', fontSize: '20px' }}>Clínicas Registradas</h2>
                    {loading ? (
                        <p className="text75">Carregando clínicas...</p>
                    ) : clinicasFiltradas.length === 0 ? (
                        <CampNotList
                            img={IMG}
                            text_p="Nenhuma clínica foi registrada"
                            text_l="Você ainda não cadastrou nenhuma clínica. Comece cadastrando sua primeira clínica!"
                            text_btn="Cadastrar sua Primeira Clínica"
                            utl_btn="/owner/clinic/register"
                        />
                    ) : (
                        clinicasFiltradas.map((item) => (
                            <CampList
                                key={item.id}
                                clinic_id={item.id}
                                clinic_logo={item.logo}
                                clinic_img={IMG}
                                clinic_name={item.nome || item.nome_fantasia}
                                clinic_cnpj={item.cnpj}
                                clinic_phone={item.telefone}
                                is_active={item.ativa}
                                ativando={ativandoId === item.id}
                                onAtivar={handleAtivar}
                            />
                        ))
                    )}
                </div>
            </main>
        </>
    );
}

export default ListClinic;

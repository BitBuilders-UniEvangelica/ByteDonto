/* IMPORTS OF COMPONENTS */
import { BrowserRouter, Routes, Route, Navigate, Link, useLocation } from "react-router-dom";
import { AuthProvider, useAuth } from "../context/AuthContext";
import ScrollToTop from "./ScrollToTop";
import { FeedbackProvider } from "../components/feedback/Feedback";

import LandingPage from "../pages/general/LandingPage";
import LoginPage from "../pages/general/LoginPage";
import CadastroPage from "../pages/general/CadastroPage";
import NotFoundPage from "../pages/general/NotFoundPage";

import ListClinic from "../pages/autenticado/clinica/ListClinic";
import ViewClinic from "../pages/autenticado/clinica/ViewClinic";
import RegisterClinic from "../pages/autenticado/clinica/RegisterClinic";
import EditClinic from "../pages/autenticado/clinica/EditClinic";
import BindClinic from "../pages/autenticado/clinica/BindClinic";

import AgendaRecepcao from "../pages/autenticado/agenda/AgendaRecepcao";
import PainelEspecialista from "../pages/autenticado/agenda/PainelEspecialista";

import ListPatients from "../pages/autenticado/pacientes/ListPatients";
import RegisterPatient from "../pages/autenticado/pacientes/RegisterPatient";
import ViewPatient from "../pages/autenticado/pacientes/ViewPatient";
import ViewRecord from "../pages/autenticado/pacientes/ViewRecord";

import Financial from "../pages/autenticado/financeiro/Financial";

import Estoque from "../pages/autenticado/estoque/Estoque";
import ItemEstoque from "../pages/autenticado/estoque/ItemEstoque";
import HistoricoEstoque from "../pages/autenticado/estoque/HistoricoEstoque";

import { PAPEIS, PREFIXOS, prefixoDoPapel, rotaInicial, temPermissao } from "../utils/rotas";

/* TELAS COMPARTILHADAS — existem em /owner, /specialist e /reception.
   - perm: permissão exigida do Especialista e da Recepção (o Dono tem todas).
   - pagina: o mesmo arquivo para todos os papéis, ou um objeto { papel: página }
     quando a tela daquele papel é outra (ex.: a agenda do Especialista). */
const TELAS = [
  { path: "dashboard",         perm: "ver_agenda",       pagina: { Dono: AgendaRecepcao, "Recepção": AgendaRecepcao, Especialista: PainelEspecialista } },
  { path: "patients",          perm: "ver_pacientes",    pagina: ListPatients },
  { path: "patient/register",  perm: "editar_pacientes", pagina: RegisterPatient },
  { path: "patient/view",      perm: "ver_pacientes",    pagina: ViewPatient },
  { path: "patient/record",    perm: "ver_prontuario",   pagina: ViewRecord },
  { path: "financial",         perm: "ver_financeiro",   pagina: Financial },
  { path: "estoque",           perm: "estoque",          pagina: Estoque },
  { path: "estoque/item/:id",  perm: "estoque",          pagina: ItemEstoque },
  { path: "estoque/historico", perm: "estoque",          pagina: HistoricoEstoque },
];

/* TELAS SÓ DO PROPRIETÁRIO (/owner/*) */
const TELAS_DONO = [
  { path: "clinic",            pagina: ListClinic },
  { path: "clinic/register",   pagina: RegisterClinic },
  { path: "view-clinic/:id",   pagina: ViewClinic },
  { path: "edit-clinic/:id",   pagina: EditClinic },
  { path: "bind-clinic/:id",   pagina: BindClinic },
  { path: "team",              pagina: BindClinic },
];

/* Tela exibida quando o usuário está autenticado mas não tem acesso à página.
   Importante: NÃO redireciona para /login — isso criaria um ciclo de
   redirecionamento (a LoginPage re-autenticaria pela sessão salva). */
function SemAcesso() {
  const { logout, user } = useAuth();
  const location = useLocation();
  const inicio = user?.perfil?.papel ? rotaInicial(user.perfil) : null;
  const temOutraTela = inicio && !inicio.endsWith("/sem-acesso") && inicio !== location.pathname;
  return (
    <div style={{
      minHeight: "calc(100vh / var(--app-zoom))", display: "flex", flexDirection: "column",
      alignItems: "center", justifyContent: "center", gap: "1rem",
      padding: "2rem", textAlign: "center", background: "var(--BackColor)",
    }}>
      <h1 style={{ margin: 0, fontSize: "22px", color: "var(--TextColor)" }}>
        Acesso não autorizado
      </h1>
      <p style={{ margin: 0, maxWidth: "440px", color: "var(--TextColor75)" }}>
        Sua conta não tem permissão para acessar esta página. Entre com uma
        conta que tenha o acesso necessário.
      </p>
      <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap", justifyContent: "center" }}>
        {temOutraTela && (
          <Link to={inicio} style={{
            padding: "11px 22px", background: "var(--PrimaryColorsTheme)",
            color: "white", borderRadius: "8px", textDecoration: "none",
            fontWeight: 700, fontSize: "14px",
          }}>
            Voltar para o início
          </Link>
        )}
        <button onClick={logout} style={{
          padding: "11px 22px",
          background: temOutraTela ? "var(--BackColor)" : "var(--PrimaryColorsTheme)",
          color: temOutraTela ? "var(--TextColor)" : "white",
          border: temOutraTela ? "1px solid var(--LineColor)" : "none", borderRadius: "8px",
          fontWeight: 700, fontSize: "14px", cursor: "pointer",
        }}>
          Sair e trocar de conta
        </button>
      </div>
    </div>
  );
}

/* ROTA PROTEGIDA — exige login, o papel dono do prefixo e a permissão da tela.
   Se alguém abre a rota de outro papel (ex.: o Dono em /reception/patients),
   é levado para a mesma tela no próprio prefixo (/owner/patients), onde a
   permissão é conferida de novo. */
function RotaProtegida({ papel, perm, children }) {
  const { token, user, loading } = useAuth();
  const location = useLocation();
  if (loading) return null;
  if (!token) return <Navigate to="/login" replace />;

  const perfil = user?.perfil;
  if (perfil?.papel !== papel) {
    const meuPrefixo = prefixoDoPapel(perfil?.papel);
    if (!meuPrefixo) return <SemAcesso />;
    const destino = location.pathname.replace(/^\/[^/]+/, `/${meuPrefixo}`) + location.search;
    return <Navigate to={destino} replace />;
  }

  if (perm && !temPermissao(perfil, perm)) return <SemAcesso />;
  return children;
}

function rotasDoPapel(papel) {
  const { prefixo } = PAPEIS[papel];
  const telas = papel === "Dono" ? [...TELAS_DONO, ...TELAS] : TELAS;
  return telas.map(({ path, perm, pagina }) => {
    const Pagina = typeof pagina === "function" ? pagina : pagina[papel];
    return (
      <Route
        key={`${prefixo}/${path}`}
        path={`/${prefixo}/${path}`}
        element={<RotaProtegida papel={papel} perm={papel === "Dono" ? null : perm}><Pagina /></RotaProtegida>}
      />
    );
  });
}

/* MAIN COMPONENT */
export function AppRoutes() {
  return (
    <BrowserRouter>
      <ScrollToTop />
      <AuthProvider>
        <FeedbackProvider>
        <Routes>
          {/* Public routes */}
          <Route path="/" element={<LandingPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/cadastro" element={<CadastroPage />} />

          {/* Rotas autenticadas: uma árvore por papel (/owner, /specialist, /reception) */}
          {Object.keys(PAPEIS).flatMap(rotasDoPapel)}
          <Route path="/owner/onboarding" element={<Navigate to="/owner/clinic" replace />} />
          {PREFIXOS.map(prefixo => (
            <Route key={prefixo} path={`/${prefixo}/sem-acesso`} element={<SemAcesso />} />
          ))}

          {/* Qualquer rota inexistente */}
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
        </FeedbackProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}
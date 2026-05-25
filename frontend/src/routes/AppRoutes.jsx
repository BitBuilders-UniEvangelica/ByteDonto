/* IMPORTS OF COMPONENTS */
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "../context/AuthContext";
import ScrollToTop from "./ScrollToTop";

import LandingPage from "../pages/general/LandingPage";
import LoginPage from "../pages/general/LoginPage";
import CadastroPage from "../pages/general/CadastroPage";

import ListClinic from "../pages/owner/ListClinic";
import ViewClinic from "../pages/owner/ViewClinic";
import RegisterClinic from "../pages/owner/RegisterClinic";
import EditClinic from "../pages/owner/EditClinic";
import BindClinic from "../pages/owner/BindClinic";
import OwnerFinancial from "../pages/owner/Financial";

import SpecialistDashboard from "../pages/specialist/Dashboard";
import SpecialistListPatients from "../pages/specialist/ListPatients";
import SpecialistViewRecord from "../pages/specialist/ViewRecord";

import ReceptionDashboard from "../pages/reception/Dashboard";
import RegisterPatient from "../pages/reception/RegisterPatient";
import ListPatients from "../pages/reception/ListPatients";
import ViewPatient from "../pages/reception/ViewPatient";

/* Tela exibida quando o usuário está autenticado mas não tem acesso à página.
   Importante: NÃO redireciona para /login — isso criaria um ciclo de
   redirecionamento (a LoginPage re-autenticaria pela sessão salva). */
function SemAcesso() {
  const { logout } = useAuth();
  return (
    <div style={{
      minHeight: "100vh", display: "flex", flexDirection: "column",
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
      <button onClick={logout} style={{
        padding: "11px 22px", background: "var(--PrimaryColorsTheme)",
        color: "white", border: "none", borderRadius: "8px",
        fontWeight: 700, fontSize: "14px", cursor: "pointer",
      }}>
        Sair e trocar de conta
      </button>
    </div>
  );
}

/* PERMISSION ROUTE — exige autenticação + acesso por papel ou permissão.
   - donoOnly: requer papel "Dono".
   - perm: requer a permissão indicada (Dono sempre tem tudo). */
function PermissionRoute({ children, perm, donoOnly }) {
  const { token, user, loading } = useAuth();
  if (loading) return null;
  if (!token) return <Navigate to="/login" replace />;

  const papel = user?.perfil?.papel;
  const ehDono = papel === "Dono";

  if (donoOnly && !ehDono) {
    return <SemAcesso />;
  }

  if (perm && !ehDono) {
    const permissoes = user?.perfil?.permissoes || {};
    if (permissoes[perm] !== true) {
      return <SemAcesso />;
    }
  }

  return children;
}

/* MAIN COMPONENT */
export function AppRoutes() {
  return (
    <BrowserRouter>
      <ScrollToTop />
      <AuthProvider>
        <Routes>
          {/* Public routes */}
          <Route path="/" element={<LandingPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/cadastro" element={<CadastroPage />} />

          {/* ROTA DO PROPRIETÁRIO */}
          <Route path="/owner/clinic" element={<PermissionRoute donoOnly><ListClinic /></PermissionRoute>} />
          <Route path="/owner/clinic/register" element={<PermissionRoute donoOnly><RegisterClinic /></PermissionRoute>} />
          <Route path="/owner/view-clinic/:id" element={<PermissionRoute donoOnly><ViewClinic /></PermissionRoute>} />
          <Route path="/owner/edit-clinic/:id" element={<PermissionRoute donoOnly><EditClinic /></PermissionRoute>} />
          <Route path="/owner/bind-clinic/:id" element={<PermissionRoute donoOnly><BindClinic /></PermissionRoute>} />
          <Route path="/owner/team" element={<PermissionRoute donoOnly><BindClinic /></PermissionRoute>} />
          <Route path="/owner/onboarding" element={<Navigate to="/owner/clinic" replace />} />
          <Route path="/owner/financial" element={<PermissionRoute donoOnly><OwnerFinancial role="owner" /></PermissionRoute>} />
          <Route path="/reception/financial" element={<PermissionRoute perm="ver_financeiro"><OwnerFinancial role="reception" /></PermissionRoute>} />

          {/* ROTA DO ESPECIALISTA (DENTISTA) */}
          <Route path="/specialist/dashboard" element={<PermissionRoute perm="ver_agenda"><SpecialistDashboard /></PermissionRoute>} />
          <Route path="/specialist/patients" element={<PermissionRoute perm="ver_pacientes"><SpecialistListPatients /></PermissionRoute>} />
          <Route path="/specialist/records" element={<PermissionRoute perm="ver_pacientes"><SpecialistListPatients /></PermissionRoute>} />
          <Route path="/specialist/patient/view" element={<PermissionRoute perm="ver_pacientes"><SpecialistViewRecord /></PermissionRoute>} />

          {/* ROTA DA RECEPÇÃO */}
          <Route path="/reception/dashboard" element={<PermissionRoute perm="ver_agenda"><ReceptionDashboard /></PermissionRoute>} />
          <Route path="/reception/patient/register" element={<PermissionRoute perm="ver_pacientes"><RegisterPatient /></PermissionRoute>} />
          <Route path="/reception/patients" element={<PermissionRoute perm="ver_pacientes"><ListPatients /></PermissionRoute>} />
          <Route path="/reception/patient/view" element={<PermissionRoute perm="ver_pacientes"><ViewPatient /></PermissionRoute>} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
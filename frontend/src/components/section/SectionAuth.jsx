/* IMPORTS OF COMPONENTS */
import { useAuth } from "../../context/AuthContext";
import { LogOut, UserRound } from "lucide-react";
import ToothIcon from "../icons/ToothIcon";
import '../../styles/Section.css'

/* MAIN COMPONENT */
function SectionAuth({ type_styles }) {
    const { user, logout } = useAuth();

    return (
        <section className={`premium-topbar ${type_styles}`}>
            <h1 id="logo">
                <span className="brand-mark">
                    <ToothIcon size={22} />
                </span>
                BYTE DONTO
            </h1>
            <div className="topbar-actions">
                <div className="user-profile">
                    <span className="user-avatar">
                        <UserRound size={18} strokeWidth={2} />
                    </span>
                    <div className="user-meta">
                        <span className="user-name">{user?.perfil?.nome || "Usuário"}</span>
                        <span className="user-role owner-badge">
                            {(user?.perfil?.papel || "").toUpperCase()}
                        </span>
                    </div>
                </div>
                <button
                    className="logout-btn"
                    onClick={logout}
                    title="Desconectar da conta"
                >
                    <LogOut size={16} strokeWidth={2} />
                    Sair
                </button>
            </div>
        </section>
    );
}

/* STANDARD EXPORT */
export default SectionAuth;

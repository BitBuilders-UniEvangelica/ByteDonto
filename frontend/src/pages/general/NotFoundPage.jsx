/* PÁGINA 404 — qualquer rota inexistente (antes o app ficava em branco). */
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { EstadoErro } from "../../components/feedback/Feedback";

const INICIO_POR_PAPEL = {
    "Recepção": { url: "/reception/dashboard", texto: "Voltar para a Agenda" },
    "Especialista": { url: "/specialist/dashboard", texto: "Voltar para a Agenda" },
    "Dono": { url: "/owner/clinic", texto: "Voltar para Minhas Clínicas" },
};

function NotFoundPage() {
    const navigate = useNavigate();
    const { token, user } = useAuth();
    const destino = token
        ? INICIO_POR_PAPEL[user?.perfil?.papel] || INICIO_POR_PAPEL.Dono
        : { url: "/", texto: "Voltar para o início" };

    return (
        <main style={{
            minHeight: "calc(100vh / var(--app-zoom))", display: "flex",
            alignItems: "center", justifyContent: "center", background: "var(--BackColor)",
        }}>
            <EstadoErro
                tipo="404"
                titulo="Página não encontrada"
                mensagem="O endereço que você tentou acessar não existe ou foi movido."
                textoBotao={destino.texto}
                onAcao={() => navigate(destino.url)}
            />
        </main>
    );
}

export default NotFoundPage;

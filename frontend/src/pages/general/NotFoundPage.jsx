/* PÁGINA 404 — qualquer rota inexistente (antes o app ficava em branco). */
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { EstadoErro } from "../../components/feedback/Feedback";
import { rotaInicial } from "../../utils/rotas";

function NotFoundPage() {
    const navigate = useNavigate();
    const { token, user } = useAuth();
    const destino = token
        ? { url: user?.perfil?.papel ? rotaInicial(user.perfil) : "/owner/clinic", texto: "Voltar para o sistema" }
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

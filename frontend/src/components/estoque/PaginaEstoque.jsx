import { useAuth } from "../../context/AuthContext";
import Section from "../section/SectionAuth";
import SideBar from "../bar/SideBar";
import { useSidebar } from "../../hooks/useSidebar";
import { estiloDoPapel } from "../../utils/rotas";
import "../../styles/clinic.css";
import "../../styles/Forms.css";
import "../../styles/Estoque.css";

/* Moldura comum das telas de estoque: topo, menu lateral e área principal. */
export default function PaginaEstoque({ children }) {
    const { user } = useAuth();
    const estilo = estiloDoPapel(user?.perfil?.papel);
    const opc_bar = useSidebar("stock");

    return (
        <>
            <Section type_styles={estilo} />
            <SideBar opc={opc_bar} styles={estilo} />
            <main className={`mainBar ${estilo}`} style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
                {children}
            </main>
        </>
    );
}

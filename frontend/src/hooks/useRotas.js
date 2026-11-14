import { useAuth } from "../context/AuthContext";
import { estiloDoPapel, prefixoDoPapel, rotaDoPapel } from "../utils/rotas";

/* Atalho para as páginas montarem links dentro do prefixo do papel logado.
   const { rota, estilo } = useRotas();  rota("patient/view?id=1") → "/reception/patient/view?id=1" */
export function useRotas() {
    const { user } = useAuth();
    const papel = user?.perfil?.papel;
    return {
        papel,
        prefixo: prefixoDoPapel(papel),
        estilo: estiloDoPapel(papel),
        rota: (caminho) => rotaDoPapel(papel, caminho),
    };
}

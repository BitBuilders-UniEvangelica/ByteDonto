import { useEffect, useState } from "react";
import { apiGetPacientesOpcoes } from "../services/api";

/* Autocomplete de pacientes com a busca feita NO SERVIDOR (até 20 resultados).
   Espera 250 ms depois da digitação e só busca a partir de 2 caracteres —
   a tela não precisa mais baixar todos os pacientes da clínica. */
export function useBuscaPacientes(token, termo) {
    const [resultado, setResultado] = useState({ termo: "", lista: [] });
    const busca = (termo || "").trim();
    const ativa = busca.length > 1;

    useEffect(() => {
        if (!ativa || !token) return undefined;
        let vigente = true;
        const t = setTimeout(() => {
            apiGetPacientesOpcoes(token, busca)
                .then(lista => { if (vigente) setResultado({ termo: busca, lista }); })
                .catch(() => { if (vigente) setResultado({ termo: busca, lista: [] }); });
        }, 250);
        return () => { vigente = false; clearTimeout(t); };
    }, [token, busca, ativa]);

    return ativa ? resultado.lista : [];
}

import { useAuth } from "../context/AuthContext";
import { rotaDoPapel, temPermissao } from "../utils/rotas";
import { Hospital, Users, CalendarDays, UserRound, Wallet, Package } from "lucide-react";

/* Definição única do menu, dirigida por permissões.
   Cada item declara como sua visibilidade é decidida:
   - donoOnly: visível apenas para o papel "Dono"
   - perm: chave de permissão (Dono sempre tem tudo)
   O campo `icon` é um componente de ícone do lucide-react.
   `caminho` é relativo ao prefixo do papel logado: o mesmo item "Pacientes"
   leva o Dono a /owner/patients, o Especialista a /specialist/patients e a
   Recepção a /reception/patients (ver utils/rotas.js). */
const MENU = [
    { id: "clinic",    name: "Clínica",    icon: Hospital,     caminho: "clinic",    donoOnly: true },
    { id: "team",      name: "Equipe",     icon: Users,        caminho: "team",      donoOnly: true },
    { id: "agenda",    name: "Agenda",     icon: CalendarDays, caminho: "dashboard", perm: "ver_agenda" },
    { id: "patients",  name: "Pacientes",  icon: UserRound,    caminho: "patients",  perm: "ver_pacientes" },
    { id: "stock",     name: "Estoque",    icon: Package,      caminho: "estoque",   perm: "estoque" },
    { id: "financial", name: "Financeiro", icon: Wallet,       caminho: "financial", perm: "ver_financeiro" },
];

/* Trata "dashboard" como equivalente a "agenda" para destacar o item certo */
function mesmoItem(itemId, activeId) {
    if (itemId === activeId) return true;
    if (itemId === "agenda" && activeId === "dashboard") return true;
    return false;
}

/* Hook unificado — retorna o menu filtrado por permissão, com as URLs no
   prefixo do papel do usuário. */
export function useSidebar(activeId) {
    const { user } = useAuth();
    const perfil = user?.perfil;
    const ehDono = perfil?.papel === "Dono";

    return MENU
        .filter(item => {
            if (item.donoOnly) return ehDono;
            if (item.perm) return temPermissao(perfil, item.perm);
            return true;
        })
        .map(item => ({
            id: item.id,
            icon: item.icon,
            name: item.name,
            url: rotaDoPapel(perfil?.papel, item.caminho),
            style: mesmoItem(item.id, activeId) ? "select" : "",
        }));
}

/* Aliases mantidos para compatibilidade — todas as páginas existentes
   continuam funcionando sem alteração. */
export function useOwnerSidebar(activeId) {
    return useSidebar(activeId);
}

export function useSpecialistSidebar(activeId) {
    return useSidebar(activeId);
}

export function useReceptionSidebar(activeId) {
    return useSidebar(activeId);
}

import { useAuth } from "../context/AuthContext";
import { usePermissao } from "./usePermissao";
import { Hospital, Users, CalendarDays, UserRound, Wallet } from "lucide-react";

/* Definição única do menu, dirigida por permissões.
   Cada item declara como sua visibilidade é decidida:
   - donoOnly: visível apenas para o papel "Dono"
   - perm: chave de permissão (Dono sempre tem tudo via usePermissao)
   O campo `icon` é um componente de ícone do lucide-react.
   As URLs de Agenda/Pacientes dependem do papel: o Especialista usa as
   telas clínicas (/specialist/*); o Dono e a Recepção usam as telas de
   gestão (/reception/*), que têm agendamento e cadastro de pacientes. */
const MENU = [
    { id: "clinic",    name: "Clínica",    icon: Hospital,    donoOnly: true },
    { id: "team",      name: "Equipe",     icon: Users,        donoOnly: true },
    { id: "agenda",    name: "Agenda",     icon: CalendarDays, perm: "ver_agenda" },
    { id: "patients",  name: "Pacientes",  icon: UserRound,    perm: "ver_pacientes" },
    { id: "financial", name: "Financeiro", icon: Wallet,       perm: "ver_financeiro" },
];

/* Trata "dashboard" como equivalente a "agenda" para destacar o item certo */
function mesmoItem(itemId, activeId) {
    if (itemId === activeId) return true;
    if (itemId === "agenda" && activeId === "dashboard") return true;
    return false;
}

/* Hook unificado — retorna o menu filtrado por permissão, com URLs
   apropriadas ao papel do usuário. */
export function useSidebar(activeId) {
    const { user } = useAuth();
    const papel = user?.perfil?.papel;
    const ehDono = papel === "Dono";
    const ehEspecialista = papel === "Especialista";

    const verAgenda     = usePermissao("ver_agenda");
    const verPacientes  = usePermissao("ver_pacientes");
    const verFinanceiro = usePermissao("ver_financeiro");

    const permitido = {
        ver_agenda: verAgenda,
        ver_pacientes: verPacientes,
        ver_financeiro: verFinanceiro,
    };

    // O Especialista usa as telas clínicas (/specialist/*); o Dono e a
    // Recepção usam as telas de gestão (/reception/*), com agendamento e
    // cadastro de pacientes. O Financeiro do Dono é o painel /owner/financial.
    const urls = {
        clinic:    "/owner/clinic",
        team:      "/owner/team",
        agenda:    ehEspecialista ? "/specialist/dashboard" : "/reception/dashboard",
        patients:  ehEspecialista ? "/specialist/patients"  : "/reception/patients",
        financial: ehDono ? "/owner/financial" : "/reception/financial",
    };

    return MENU
        .filter(item => {
            if (item.donoOnly) return ehDono;
            if (item.perm) return permitido[item.perm];
            return true;
        })
        .map(item => ({
            id: item.id,
            icon: item.icon,
            name: item.name,
            url: urls[item.id],
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

export function formatarDataHora(d) {
    const data = d instanceof Date ? d : new Date(d);
    return `${data.toLocaleDateString("pt-BR")} às ${data.toLocaleTimeString("pt-BR")}`;
}

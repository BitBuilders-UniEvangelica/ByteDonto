/* Rotas por papel.
   Cada papel só navega dentro do próprio prefixo:
     Dono → /owner/*   Especialista → /specialist/*   Recepção → /reception/*
   A mesma tela (ex.: pacientes) existe nos três prefixos e usa o mesmo arquivo
   de página; o que muda entre os papéis é a permissão exigida (ver AppRoutes). */

export const PAPEIS = {
    Dono:         { prefixo: "owner",      estilo: "owner" },
    Especialista: { prefixo: "specialist", estilo: "specialist" },
    "Recepção":   { prefixo: "reception",  estilo: "reception" },
};

export const PREFIXOS = Object.values(PAPEIS).map(p => p.prefixo);

export function prefixoDoPapel(papel) {
    return PAPEIS[papel]?.prefixo || null;
}

export function estiloDoPapel(papel) {
    return PAPEIS[papel]?.estilo || "reception";
}

/* Monta a URL de uma tela para o papel: rotaDoPapel("Dono", "patients") → "/owner/patients" */
export function rotaDoPapel(papel, caminho = "") {
    const prefixo = prefixoDoPapel(papel);
    if (!prefixo) return "/";
    return `/${prefixo}/${String(caminho).replace(/^\/+/, "")}`.replace(/\/$/, "");
}

/* true se o perfil tem a permissão. O Dono sempre tem tudo. */
export function temPermissao(perfil, chave) {
    if (!perfil) return false;
    if (perfil.papel === "Dono") return true;
    return (perfil.permissoes || {})[chave] === true;
}

/* Primeira tela que o usuário pode abrir depois do login. */
export function rotaInicial(perfil) {
    const papel = perfil?.papel;
    if (papel === "Dono") return rotaDoPapel(papel, "clinic");
    if (!prefixoDoPapel(papel)) return "/";
    const opcoes = [
        ["ver_agenda", "dashboard"],
        ["ver_pacientes", "patients"],
        ["ver_financeiro", "financial"],
        ["estoque", "estoque"],
    ];
    const tela = opcoes.find(([perm]) => temPermissao(perfil, perm));
    return tela ? rotaDoPapel(papel, tela[1]) : rotaDoPapel(papel, "sem-acesso");
}

/* API BASE URL — troca para a URL do Render quando fizer o deploy */
const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

/* --- AUTH --- */
export async function apiRegistro(nome, email, password) {
    const res = await fetch(`${API_URL}/api/auth/registro`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ nome, email, password }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Erro ao criar conta");
    return data;
}

export async function apiLogin(email, password) {
    const res = await fetch(`${API_URL}/api/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Erro ao fazer login");
    return data;
}

export async function apiMe(token) {
    const res = await fetch(`${API_URL}/api/auth/me`, {
        headers: { Authorization: `Bearer ${token}` },
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Sessão expirada");
    return data;
}

/* --- PACIENTES --- */
/* Monta a query string ignorando valores vazios. */
function qs(params = {}) {
    const q = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined && v !== null && v !== "") q.set(k, v);
    });
    const s = q.toString();
    return s ? `?${s}` : "";
}

/* Lista PAGINADA: { items, page, per_page, total }.
   A busca (nome, CPF ou telefone) é feita no banco. */
export async function apiGetPacientes(token, { page = 1, perPage = 20, busca = "" } = {}) {
    const res = await fetch(`${API_URL}/api/pacientes/` + qs({ page, per_page: perPage, busca }), {
        headers: { Authorization: `Bearer ${token}` },
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Erro ao buscar pacientes");
    return data;
}

/* Lista curta (id, nome, CPF, telefone) para campos de seleção.
   Com busca: até 20 resultados (autocomplete). Sem busca: todos, por nome. */
export async function apiGetPacientesOpcoes(token, busca = "") {
    const res = await fetch(`${API_URL}/api/pacientes/opcoes` + qs({ busca }), {
        headers: { Authorization: `Bearer ${token}` },
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Erro ao buscar pacientes");
    return Array.isArray(data) ? data : [];
}

export async function apiGetPaciente(token, pacienteId) {
    const res = await fetch(`${API_URL}/api/pacientes/${pacienteId}`, {
        headers: { Authorization: `Bearer ${token}` },
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Erro ao buscar paciente");
    return data;
}

export async function apiCriarPaciente(token, pacienteData) {
    const res = await fetch(`${API_URL}/api/pacientes/`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(pacienteData),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Erro ao cadastrar paciente");
    return data;
}

export async function apiAtualizarPaciente(token, pacienteId, pacienteData) {
    const res = await fetch(`${API_URL}/api/pacientes/${pacienteId}`, {
        method: "PUT",
        headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(pacienteData),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Erro ao atualizar paciente");
    return data;
}

/* --- CONSULTAS --- */
/* filtros opcionais: { paciente_id, data_inicio, data_fim } (datas AAAA-MM-DD).
   Sem page/per_page a resposta continua sendo uma lista. */
export async function apiGetConsultas(token, filtros = {}) {
    const res = await fetch(`${API_URL}/api/consultas/` + qs(filtros), {
        headers: { Authorization: `Bearer ${token}` },
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Erro ao buscar consultas");
    return data;
}

export async function apiCriarConsulta(token, consultaData) {
    const res = await fetch(`${API_URL}/api/consultas/`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(consultaData),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Erro ao agendar consulta");
    return data;
}

export async function apiAtualizarConsulta(token, id, dados) {
    const res = await fetch(`${API_URL}/api/consultas/${id}`, {
        method: "PUT",
        headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(dados),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Erro ao atualizar consulta");
    return data;
}

/* --- CLÍNICAS --- */
export async function apiGetClinics(token) {
    const res = await fetch(`${API_URL}/api/clinicas/`, {
        headers: { Authorization: `Bearer ${token}` },
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Erro ao buscar clínicas");
    return data;
}

export async function apiCreateClinic(token, clinicData) {
    const res = await fetch(`${API_URL}/api/clinicas/`, {
        method: "POST",
        headers: { 
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}` 
        },
        body: JSON.stringify(clinicData),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Erro ao criar clínica");
    return data;
}
export async function apiGetClinic(token, clinicaId) {
    const res = await fetch(`${API_URL}/api/clinicas/${clinicaId}`, {
        headers: { Authorization: `Bearer ${token}` },
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Erro ao buscar clínica");
    return data;
}

export async function apiUpdateClinic(token, clinicaId, clinicData) {
    const res = await fetch(`${API_URL}/api/clinicas/${clinicaId}`, {
        method: "PUT",
        headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`
        },
        body: JSON.stringify(clinicData),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Erro ao atualizar clínica");
    return data;
}

export async function apiAtivarClinica(token, clinicaId) {
    const res = await fetch(`${API_URL}/api/clinicas/${clinicaId}/ativar`, {
        method: "PUT",
        headers: { Authorization: `Bearer ${token}` },
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Erro ao trocar de clínica");
    return data;
}

/* --- EQUIPE / USUÁRIOS --- */
export async function apiGetEquipe(token) {
    const res = await fetch(`${API_URL}/api/usuarios/`, {
        headers: { Authorization: `Bearer ${token}` },
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Erro ao buscar equipe");
    return data;
}

export async function apiCriarMembro(token, membroData) {
    const res = await fetch(`${API_URL}/api/usuarios/criar`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(membroData),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Erro ao criar membro");
    return data;
}

export async function apiRemoverMembro(token, usuarioId) {
    const res = await fetch(`${API_URL}/api/usuarios/${usuarioId}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Erro ao remover membro");
    return data;
}

export async function apiAtualizarMembro(token, usuarioId, dadosAtualizados) {
    const res = await fetch(`${API_URL}/api/usuarios/${usuarioId}`, {
        method: "PUT",
        headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(dadosAtualizados),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Erro ao atualizar membro");
    return data;
}

export async function apiRedefinirSenha(token, usuarioId, senha) {
    const res = await fetch(`${API_URL}/api/usuarios/${usuarioId}/senha`, {
        method: "PUT",
        headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ senha }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Erro ao redefinir senha");
    return data;
}

export async function apiGetPermissoes(token, usuarioId) {
    const res = await fetch(`${API_URL}/api/usuarios/${usuarioId}/permissoes`, {
        headers: { Authorization: `Bearer ${token}` },
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Erro ao buscar permissões");
    return data;
}

export async function apiAtualizarPermissoes(token, usuarioId, permissoes) {
    const res = await fetch(`${API_URL}/api/usuarios/${usuarioId}/permissoes`, {
        method: "PATCH",
        headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ permissoes }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Erro ao atualizar permissões");
    return data;
}

/* --- FINANCEIRO --- */
/* Com { page } devolve { items, page, per_page, total, resumo_mes };
   sem page devolve a lista (usado na ficha do paciente com pacienteId). */
export async function apiGetFinanceiro(token, { status, page, perPage, pacienteId } = {}) {
    const url = `${API_URL}/api/financeiro/` + qs({
        status_pagamento: status,
        page,
        per_page: page ? perPage || 20 : undefined,
        paciente_id: pacienteId,
    });
    const res = await fetch(url, {
        headers: { Authorization: `Bearer ${token}` },
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Erro ao buscar lançamentos financeiros");
    return data;
}

/* Totais dos cards e gráficos (somados no servidor). */
export async function apiGetResumoFinanceiro(token) {
    const res = await fetch(`${API_URL}/api/financeiro/resumo`, {
        headers: { Authorization: `Bearer ${token}` },
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Erro ao buscar o resumo financeiro");
    return data;
}

export async function apiCriarLancamento(token, lancamentoData) {
    const res = await fetch(`${API_URL}/api/financeiro/`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(lancamentoData),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Erro ao criar lançamento");
    return data;
}

export async function apiGetRepasses(token, mes = null) {
    const url = mes
        ? `${API_URL}/api/financeiro/repasses?mes=${encodeURIComponent(mes)}`
        : `${API_URL}/api/financeiro/repasses`;
    const res = await fetch(url, { headers: { Authorization: `Bearer ${token}` } });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Erro ao buscar repasses");
    return data;
}

export async function apiAtualizarLancamento(token, id, lancamentoData) {
    const res = await fetch(`${API_URL}/api/financeiro/${id}`, {
        method: "PUT",
        headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(lancamentoData),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Erro ao atualizar lançamento");
    return data;
}

/* --- PLANOS DE TRATAMENTO --- */
export async function apiGetPlanos(token, pacienteId) {
    const res = await fetch(`${API_URL}/api/planos/?paciente_id=${pacienteId}`, { headers: { Authorization: `Bearer ${token}` } });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Erro ao buscar planos");
    return data;
}

export async function apiCriarPlano(token, payload) {
    const res = await fetch(`${API_URL}/api/planos/`, { method: "POST", headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` }, body: JSON.stringify(payload) });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Erro ao criar plano");
    return data;
}

export async function apiAtualizarPlanoItem(token, planoId, itemId, payload) {
    const res = await fetch(`${API_URL}/api/planos/${planoId}/itens/${itemId}`, { method: "PUT", headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` }, body: JSON.stringify(payload) });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Erro");
    return data;
}

/* --- IMAGENS --- */
export async function apiGetImagens(token, pacienteId) {
    const res = await fetch(`${API_URL}/api/imagens/?paciente_id=${pacienteId}`, { headers: { Authorization: `Bearer ${token}` } });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Erro");
    return Array.isArray(data) ? data : [];
}

export async function apiUploadImagem(token, pacienteId, file, tipo = "imagem") {
    const fd = new FormData();
    fd.append("file", file);
    fd.append("paciente_id", pacienteId);
    fd.append("tipo", tipo);
    const res = await fetch(`${API_URL}/api/imagens/upload`, { method: "POST", headers: { Authorization: `Bearer ${token}` }, body: fd });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Erro no upload");
    return data;
}

export async function apiDeletarImagem(token, imagemId) {
    const res = await fetch(`${API_URL}/api/imagens/${imagemId}`, { method: "DELETE", headers: { Authorization: `Bearer ${token}` } });
    if (!res.ok) { const d = await res.json(); throw new Error(d.error || "Erro"); }
}

/* --- DASHBOARD MÉTRICAS --- */
// clinicaId opcional: o Dono pode pedir métricas de outra clínica que ele possui.
export async function apiGetMetricas(token, clinicaId = null) {
    const url = clinicaId
        ? `${API_URL}/api/dashboard/metricas?clinica_id=${encodeURIComponent(clinicaId)}`
        : `${API_URL}/api/dashboard/metricas`;
    const res = await fetch(url, {
        headers: { Authorization: `Bearer ${token}` },
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Erro ao buscar métricas");
    return data;
}

/* --- ESTOQUE --- */
async function reqEstoque(token, caminho, { method = "GET", body, erro = "Erro no estoque" } = {}) {
    const res = await fetch(`${API_URL}/api/estoque${caminho}`, {
        method,
        headers: {
            Authorization: `Bearer ${token}`,
            ...(body ? { "Content-Type": "application/json" } : {}),
        },
        body: body ? JSON.stringify(body) : undefined,
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || erro);
    return data;
}

export const apiGetItensEstoque = (token) =>
    reqEstoque(token, "/itens", { erro: "Erro ao buscar itens do estoque" });
export const apiGetItemEstoque = (token, id) =>
    reqEstoque(token, `/itens/${id}`, { erro: "Erro ao buscar o item" });
export const apiCriarItemEstoque = (token, dados) =>
    reqEstoque(token, "/itens", { method: "POST", body: dados, erro: "Erro ao salvar o item" });
export const apiAtualizarItemEstoque = (token, id, dados) =>
    reqEstoque(token, `/itens/${id}`, { method: "PUT", body: dados, erro: "Erro ao atualizar o item" });
export const apiRemoverItemEstoque = (token, id) =>
    reqEstoque(token, `/itens/${id}`, { method: "DELETE", erro: "Erro ao remover o item" });

export const apiRegistrarEntradaEstoque = (token, dados) =>
    reqEstoque(token, "/entradas", { method: "POST", body: dados, erro: "Erro ao registrar a entrada" });
export const apiRegistrarSaidaEstoque = (token, dados) =>
    reqEstoque(token, "/saidas", { method: "POST", body: dados, erro: "Erro ao registrar a saída" });

export function apiGetMovimentacoesEstoque(token, { itemId, tipo, limit } = {}) {
    const qs = new URLSearchParams();
    if (itemId) qs.set("item_id", itemId);
    if (tipo) qs.set("tipo", tipo);
    if (limit) qs.set("limit", limit);
    const sufixo = qs.toString() ? `?${qs}` : "";
    return reqEstoque(token, `/movimentacoes${sufixo}`, { erro: "Erro ao buscar o histórico" });
}
export const apiGetResumoEstoque = (token, dias = 30) =>
    reqEstoque(token, `/resumo?dias=${dias}`, { erro: "Erro ao buscar o resumo do estoque" });

export const apiGetFornecedores = (token) =>
    reqEstoque(token, "/fornecedores", { erro: "Erro ao buscar fornecedores" });
export const apiCriarFornecedor = (token, dados) =>
    reqEstoque(token, "/fornecedores", { method: "POST", body: dados, erro: "Erro ao salvar o fornecedor" });
export const apiAtualizarFornecedor = (token, id, dados) =>
    reqEstoque(token, `/fornecedores/${id}`, { method: "PUT", body: dados, erro: "Erro ao atualizar o fornecedor" });

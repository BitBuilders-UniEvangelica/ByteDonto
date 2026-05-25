/* API BASE URL — troca para a URL do Render quando fizer o deploy */
const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

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
export async function apiGetPacientes(token) {
    const res = await fetch(`${API_URL}/api/pacientes/`, {
        headers: { Authorization: `Bearer ${token}` },
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Erro ao buscar pacientes");
    return data;
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
export async function apiGetConsultas(token) {
    const res = await fetch(`${API_URL}/api/consultas/`, {
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
export async function apiGetFinanceiro(token, status = null) {
    const url = status
        ? `${API_URL}/api/financeiro/?status_pagamento=${encodeURIComponent(status)}`
        : `${API_URL}/api/financeiro/`;
    const res = await fetch(url, {
        headers: { Authorization: `Bearer ${token}` },
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Erro ao buscar lançamentos financeiros");
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
export async function apiGetMetricas(token) {
    const res = await fetch(`${API_URL}/api/dashboard/metricas`, {
        headers: { Authorization: `Bearer ${token}` },
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Erro ao buscar métricas");
    return data;
}

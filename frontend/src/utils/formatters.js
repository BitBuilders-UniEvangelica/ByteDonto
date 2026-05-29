// Exibição — recebe valor bruto do banco, retorna string formatada

export function formatCPF(v) {
    if (!v) return "—";
    const d = String(v).replace(/\D/g, "").slice(0, 11);
    if (d.length === 11) return `${d.slice(0,3)}.${d.slice(3,6)}.${d.slice(6,9)}-${d.slice(9)}`;
    return v;
}

export function formatPhone(v) {
    if (!v) return "—";
    const d = String(v).replace(/\D/g, "").slice(0, 11);
    if (d.length === 11) return `(${d.slice(0,2)}) ${d.slice(2,7)}-${d.slice(7)}`;
    if (d.length === 10) return `(${d.slice(0,2)}) ${d.slice(2,6)}-${d.slice(6)}`;
    return v;
}

export function formatDate(v) {
    if (!v) return "—";
    try {
        // "2024-01-15" → "15/01/2024" sem converter timezone
        const [year, month, day] = String(v).split("T")[0].split("-");
        if (year && month && day) return `${day}/${month}/${year}`;
        return new Date(v).toLocaleDateString("pt-BR");
    } catch {
        return v;
    }
}

export function formatCurrency(v) {
    return Number(v || 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

export function calcIdade(dataString) {
    if (!dataString) return null;
    const [year, month, day] = String(dataString).split("T")[0].split("-");
    const nascimento = new Date(Number(year), Number(month) - 1, Number(day));
    const hoje = new Date();
    let idade = hoje.getFullYear() - nascimento.getFullYear();
    const m = hoje.getMonth() - nascimento.getMonth();
    if (m < 0 || (m === 0 && hoje.getDate() < nascimento.getDate())) idade--;
    return idade;
}

// Rótulo " (34 anos)" para exibição; string vazia se não houver data válida.
export function idadeLabel(dataString) {
    const idade = calcIdade(dataString);
    return idade != null ? ` (${idade} anos)` : "";
}

// Máscaras de input — usadas em onChange para formatar enquanto o usuário digita

export function maskCPF(v) {
    const d = String(v).replace(/\D/g, "").slice(0, 11);
    if (d.length <= 3)  return d;
    if (d.length <= 6)  return `${d.slice(0,3)}.${d.slice(3)}`;
    if (d.length <= 9)  return `${d.slice(0,3)}.${d.slice(3,6)}.${d.slice(6)}`;
    return `${d.slice(0,3)}.${d.slice(3,6)}.${d.slice(6,9)}-${d.slice(9)}`;
}

export function maskPhone(v) {
    const d = String(v).replace(/\D/g, "").slice(0, 11);
    if (d.length <= 2)  return d.length ? `(${d}` : "";
    if (d.length <= 7)  return `(${d.slice(0,2)}) ${d.slice(2)}`;
    if (d.length <= 11) return `(${d.slice(0,2)}) ${d.slice(2,7)}-${d.slice(7)}`;
    return v;
}

export function maskCEP(v) {
    const d = String(v).replace(/\D/g, "").slice(0, 8);
    if (d.length <= 5) return d;
    return `${d.slice(0,5)}-${d.slice(5)}`;
}

export function maskRG(v) {
    return String(v).replace(/\D/g, "").slice(0, 9);
}

export function maskCNPJ(v) {
    const d = String(v).replace(/\D/g, "").slice(0, 14);
    if (d.length <= 2)  return d;
    if (d.length <= 5)  return `${d.slice(0,2)}.${d.slice(2)}`;
    if (d.length <= 8)  return `${d.slice(0,2)}.${d.slice(2,5)}.${d.slice(5)}`;
    if (d.length <= 12) return `${d.slice(0,2)}.${d.slice(2,5)}.${d.slice(5,8)}/${d.slice(8)}`;
    return `${d.slice(0,2)}.${d.slice(2,5)}.${d.slice(5,8)}/${d.slice(8,12)}-${d.slice(12)}`;
}

// Exibição de CNPJ — recebe valor bruto do banco, retorna string formatada

export function formatCNPJ(v) {
    if (!v) return "—";
    const d = String(v).replace(/\D/g, "").slice(0, 14);
    if (d.length === 14) return `${d.slice(0,2)}.${d.slice(2,5)}.${d.slice(5,8)}/${d.slice(8,12)}-${d.slice(12)}`;
    return v;
}

// Validações — recebem valor com ou sem máscara, retornam true/false

export function validarCPF(v) {
    const d = String(v || "").replace(/\D/g, "");
    if (d.length !== 11) return false;
    if (/^(\d)\1{10}$/.test(d)) return false;

    let soma = 0;
    for (let i = 0; i < 9; i++) soma += Number(d[i]) * (10 - i);
    let resto = (soma * 10) % 11;
    if (resto === 10) resto = 0;
    if (resto !== Number(d[9])) return false;

    soma = 0;
    for (let i = 0; i < 10; i++) soma += Number(d[i]) * (11 - i);
    resto = (soma * 10) % 11;
    if (resto === 10) resto = 0;
    if (resto !== Number(d[10])) return false;

    return true;
}

export function validarCNPJ(v) {
    const d = String(v || "").replace(/\D/g, "");
    if (d.length !== 14) return false;
    if (/^(\d)\1{13}$/.test(d)) return false;

    const calcDigito = (base, pesos) => {
        let soma = 0;
        for (let i = 0; i < pesos.length; i++) soma += Number(base[i]) * pesos[i];
        const resto = soma % 11;
        return resto < 2 ? 0 : 11 - resto;
    };

    const pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2];
    const pesos2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2];

    const dig1 = calcDigito(d, pesos1);
    if (dig1 !== Number(d[12])) return false;

    const dig2 = calcDigito(d, pesos2);
    if (dig2 !== Number(d[13])) return false;

    return true;
}

export function validarEmail(v) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(String(v || "").trim());
}

export function validarTelefone(v) {
    const d = String(v || "").replace(/\D/g, "");
    return d.length === 10 || d.length === 11;
}

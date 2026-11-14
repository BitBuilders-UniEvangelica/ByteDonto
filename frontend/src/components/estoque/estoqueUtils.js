/* Constantes e formatações do módulo de estoque (espelham as regras do backend). */

export const CATEGORIAS = ["Material", "Insumo"];
export const UNIDADES = ["un", "cx", "pct", "par", "ml", "l", "g", "kg", "frasco", "ampola", "tubo", "seringa", "rolo"];
export const MOTIVOS_SAIDA = [
    "Uso em procedimento", "Vencimento", "Perda / avaria", "Ajuste de inventário", "Doação / transferência",
];

// Lote que vence em até N dias aparece com o alerta "Vence em X dias"
export const DIAS_ALERTA_VENCIMENTO = 60;

/* Data de hoje no fuso local, no formato AAAA-MM-DD (o input type="date" usa esse formato). */
export function hojeISO() {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

/* Quantidade sem casas decimais quando é inteira: 12 → "12", 2.5 → "2,5". */
export function formatQtd(v) {
    return Number(v || 0).toLocaleString("pt-BR", { maximumFractionDigits: 2 });
}

/* Dias até a data (AAAA-MM-DD), contando pelo calendário local. Negativo = já passou. */
export function diasAte(dataISO) {
    if (!dataISO) return null;
    const [a, m, d] = String(dataISO).slice(0, 10).split("-").map(Number);
    const alvo = new Date(a, m - 1, d);
    const hoje = new Date();
    hoje.setHours(0, 0, 0, 0);
    return Math.round((alvo - hoje) / 86400000);
}

/* Classe do chip de status do item. */
export const CLASSE_STATUS = { Normal: "normal", "Estoque baixo": "baixo", Esgotado: "esgotado" };

/* Status do lote pela validade: { rotulo, classe } */
export function statusLote(validade) {
    const dias = diasAte(validade);
    if (dias === null) return { rotulo: "Sem validade", classe: "normal" };
    if (dias < 0) return { rotulo: "Vencido", classe: "vencido" };
    if (dias === 0) return { rotulo: "Vence hoje", classe: "vencido" };
    if (dias <= DIAS_ALERTA_VENCIMENTO) return { rotulo: `Vence em ${dias} ${dias === 1 ? "dia" : "dias"}`, classe: "baixo" };
    return { rotulo: "Normal", classe: "normal" };
}

/* Texto da coluna "Motivo" de uma movimentação.
   Saída: "Uso em procedimento — Restauração dente 36 (Maria Souza)"
   Entrada: "Compra / reposição — NF 004692 · Dental Sul" */
export function descreverMotivo(m) {
    const partes = [m.motivo || (m.tipo === "Entrada" ? "Entrada" : "Saída")];
    if (m.tipo === "Saída") {
        const detalhe = [m.procedimento, m.paciente?.nome && `(${m.paciente.nome})`].filter(Boolean).join(" ");
        if (detalhe) partes.push(detalhe);
    } else {
        const detalhe = [m.nota_fiscal && `NF ${m.nota_fiscal}`, m.fornecedor?.nome].filter(Boolean).join(" · ");
        if (detalhe) partes.push(detalhe);
    }
    return partes.join(" — ");
}

/* "+8 un" para entrada, "−1 un" para saída */
export function qtdComSinal(m, unidade) {
    const sinal = m.tipo === "Entrada" ? "+" : "−";
    return `${sinal}${formatQtd(m.quantidade)}${unidade ? ` ${unidade}` : ""}`;
}

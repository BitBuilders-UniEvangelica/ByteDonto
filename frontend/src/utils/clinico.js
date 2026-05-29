/*
 * Lógica clínica AUXILIAR do ByteDonto: classificação ASA e dose máxima de
 * anestésico local. IMPORTANTE: são cálculos de APOIO à decisão. A
 * responsabilidade clínica e legal é sempre do cirurgião-dentista que assina.
 *
 * Fontes: ASA Physical Status Classification (ASA, aprovado 2014, rev. 2020);
 * Malamed, Handbook of Local Anesthesia, 7ª ed. (doses máximas recomendadas).
 */

/* ============================ ASA ============================ */

export const ROMANO = { 1: "I", 2: "II", 3: "III", 4: "IV", 5: "V", 6: "VI" };

export const ASA_DESCRICAO = {
    1: "Paciente saudável, sem doença sistêmica.",
    2: "Doença sistêmica leve, sem limitação funcional (ex.: hipertensão ou diabetes controlados, gestante, fumante).",
    3: "Doença sistêmica grave, com limitação funcional (ex.: HAS/diabetes mal controlados, DPOC, doença renal em diálise).",
    4: "Doença sistêmica grave que é ameaça constante à vida (ex.: infarto/AVC recente, angina instável).",
    5: "Paciente moribundo, sem expectativa de sobreviver sem a intervenção.",
    6: "Morte encefálica, doador de órgãos.",
};

/* Calcula IMC. Retorna null se faltar peso/altura. */
export function calcularIMC(pesoKg, alturaCm) {
    const p = Number(pesoKg);
    const a = Number(alturaCm);
    if (!p || !a) return null;
    const m = a / 100;
    return p / (m * m);
}

/*
 * Deriva uma SUGESTÃO de classificação ASA a partir da anamnese, por
 * palavras-chave. Combina pela PIOR classe encontrada (ASA não soma).
 * ASA V/VI nunca são derivados automaticamente — exigem marcação manual.
 * Retorna { classe, motivos: [], revisar: true }.
 */
export function classificarASA(anamnese = {}) {
    const cond = `${anamnese.condicoes || ""} ${anamnese.tratamento_medico_qual || ""} ${anamnese.medicacoes || ""}`.toLowerCase();
    const drogas = `${anamnese.drogas || ""}`.toLowerCase();
    const imc = calcularIMC(anamnese.peso_kg, anamnese.altura_cm);

    let classe = 1;
    const motivos = [];
    const tem = (texto, termos) => termos.some((t) => texto.includes(t));
    const sobe = (nivel, motivo) => {
        if (nivel > classe) classe = nivel;
        motivos.push(`ASA ${ROMANO[nivel]} — ${motivo}`);
    };

    // ---- ASA II (doença leve / controlada) ----
    if (tem(cond, ["hipertens", "pressão alta"])) sobe(2, "hipertensão");
    if (tem(cond, ["diabet"])) sobe(2, "diabetes");
    if (tem(cond, ["asma", "rinite", "hipotireoid", "hipertireoid"])) sobe(2, "doença sistêmica leve");
    if (tem(cond, ["gestante", "grávida", "gravida", "gestação"])) sobe(2, "gestação");
    if (tem(drogas, ["fuma", "tabag", "cigarro", "fumante"])) sobe(2, "tabagismo");
    if (imc != null && imc >= 30 && imc < 40) sobe(2, `obesidade (IMC ${imc.toFixed(1)})`);

    // ---- ASA III (doença grave / limitante) ----
    if (tem(cond, ["mal controlad", "descompensad", "não controlad"])) sobe(3, "doença sistêmica mal controlada");
    if (tem(cond, ["dpoc", "enfisema"])) sobe(3, "DPOC");
    if (tem(cond, ["insuficiência renal", "insuf renal", "diálise", "dialise"])) sobe(3, "doença renal grave / diálise");
    if (tem(cond, ["marca-passo", "marcapasso", "marca passo"])) sobe(3, "marca-passo");
    if (tem(cond, ["epilepsia", "convuls"])) sobe(3, "epilepsia");
    if (tem(cond, ["hepatite", "cirrose"])) sobe(3, "doença hepática");
    if (tem(cond, ["infarto", "avc", "derrame", "stent", "ponte de safena", "angina"])) sobe(3, "doença cardiovascular relevante");
    if (tem(drogas, ["alcoolismo", "etilista", "depend", "cocaína", "cocaina", "crack", "drogas ilícitas", "drogas ilicitas"])) sobe(3, "dependência química");
    if (imc != null && imc >= 40) sobe(3, `obesidade grave (IMC ${imc.toFixed(1)})`);

    // ---- ASA IV (ameaça constante à vida) — termos explícitos de gravidade ----
    if (tem(cond, ["infarto recente", "avc recente", "angina instável", "angina instavel", "insuficiência cardíaca grave", "ic grave"])) {
        sobe(4, "evento cardiovascular grave/recente");
    }

    return { classe, motivos, revisar: true };
}

/* ====================== ANESTÉSICO LOCAL ====================== */

/*
 * Tubete/cartucho padrão brasileiro = 1,8 mL.
 * mgKg = dose máxima recomendada por kg (adulto, com vasoconstritor);
 * maxMg = teto absoluto por sessão; mgKgPediatrico = limite na criança.
 * Valores: Malamed 7ª ed. / consenso clínico.
 */
export const TUBETE_ML = 1.8;

export const ANESTESICOS = {
    lido2_epi: { nome: "Lidocaína 2% c/ epinefrina", mgPorML: 20, mgKg: 7.0, maxMg: 500, mgKgPediatrico: 4.4, temVaso: true },
    artic4_epi: { nome: "Articaína 4% c/ epinefrina", mgPorML: 40, mgKg: 7.0, maxMg: 500, mgKgPediatrico: 7.0, temVaso: true, restricaoIdade: "Não recomendada em menores de 4 anos." },
    mepi2_epi: { nome: "Mepivacaína 2% c/ epinefrina", mgPorML: 20, mgKg: 6.6, maxMg: 400, mgKgPediatrico: 4.4, temVaso: true },
    mepi3: { nome: "Mepivacaína 3% (sem vasoconstritor)", mgPorML: 30, mgKg: 6.6, maxMg: 400, mgKgPediatrico: 4.4, temVaso: false },
    prilo3_feli: { nome: "Prilocaína 3% c/ felipressina", mgPorML: 30, mgKg: 8.0, maxMg: 600, mgKgPediatrico: 8.0, temVaso: true },
};

const arred1 = (n) => Math.round(n * 10) / 10;

/*
 * Calcula a dose máxima de anestésico para o paciente.
 * opcoes: { idade, cardiopata, hepatopata, gestante }
 * Retorna { erro } se faltar peso, senão:
 * { anestesico, dose_mg, tubetes, mgKgUsado, mgPorTubete, avisos: [] }
 */
export function calcularDoseAnestesico(pesoKg, chave, opcoes = {}) {
    const a = ANESTESICOS[chave];
    if (!a) return { erro: "Selecione um anestésico." };

    const peso = Number(pesoKg);
    if (!peso || peso <= 0) {
        return { erro: "Informe o peso do paciente para calcular a dose." };
    }

    const { idade, cardiopata, hepatopata, gestante } = opcoes;
    const ehCrianca = Number.isFinite(idade) && idade < 13;
    const ehIdoso = Number.isFinite(idade) && idade >= 65;
    const mgPorTubete = a.mgPorML * TUBETE_ML;
    const avisos = [];

    // Na criança usa-se SEMPRE a dose por peso (nunca o teto absoluto do adulto).
    const mgKg = ehCrianca ? a.mgKgPediatrico : a.mgKg;
    const dosePorPeso = mgKg * peso;
    let doseMg = dosePorPeso;
    // No adulto, o teto absoluto por sessão é o limite máximo (independe do peso).
    const limitadoPorTeto = !ehCrianca && dosePorPeso > a.maxMg;
    if (!ehCrianca) doseMg = Math.min(doseMg, a.maxMg);

    if (limitadoPorTeto) {
        avisos.push(`Limite atingido: a dose foi limitada ao teto máximo absoluto de ${a.maxMg} mg por sessão (Malamed, 7ª ed.).`);
    }

    // Ajuste conservador (~⅔) para idoso/hepatopata: metabolismo das amidas reduzido.
    if (ehIdoso || hepatopata) {
        doseMg = doseMg * (2 / 3);
        avisos.push("Idoso ou hepatopata: dose reduzida (~⅔) — metabolismo hepático diminuído.");
    }

    if (ehCrianca) {
        avisos.push("Paciente pediátrico: dose calculada apenas pelo peso (sem o teto do adulto). Peso é obrigatório.");
        if (chave === "artic4_epi" && idade < 4) {
            avisos.push("Articaína não é recomendada em menores de 4 anos.");
        }
    }

    // Em cardiopata, com anestésico que tem vasoconstritor, o limitante passa a
    // ser a EPINEFRINA (máx ~0,04 mg/sessão ≈ 2 tubetes 1:100.000), não o sal.
    if (cardiopata && a.temVaso) {
        avisos.push("Cardiopata: o fator limitante é a epinefrina (máx. ~0,04 mg/sessão ≈ 2 tubetes 1:100.000). Considere mepivacaína 3% sem vaso ou prilocaína c/ felipressina.");
    }
    if (gestante && chave === "prilo3_feli") {
        avisos.push("Gestante: evite felipressina próximo ao termo (ação ocitócica). Lidocaína c/ epinefrina é a mais estabelecida.");
    }

    const tubetes = doseMg / mgPorTubete;

    return {
        anestesico: a.nome,
        dose_mg: arred1(doseMg),
        tubetes: Math.floor(tubetes * 10) / 10, // arredonda pra baixo (segurança)
        mgKgUsado: mgKg,
        mgPorTubete: arred1(mgPorTubete),
        tetoAbsoluto: a.maxMg,
        limitadoPorTeto,
        ehCrianca,
        restricaoIdade: a.restricaoIdade || null,
        avisos,
    };
}

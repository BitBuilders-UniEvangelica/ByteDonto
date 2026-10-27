import { useState } from "react";
import { X } from "lucide-react";

/* ------------------------------------------------------------------ */
/* Estados clínicos                                                    */
/* ------------------------------------------------------------------ */
const STATUS = {
    "Higido":            { cor: "#F4EFE3", corBorda: "#CFC4A8", label: "Hígido (Saudável)", claro: true },
    "Carie":             { cor: "#EF4444", corBorda: "#B91C1C", label: "Cárie" },
    "Restaurado":        { cor: "#0E7490", corBorda: "#155E75", label: "Restaurado" },
    "Coroa":             { cor: "#F59E0B", corBorda: "#B45309", label: "Coroa / Prótese" },
    "Extracao Indicada": { cor: "#F97316", corBorda: "#C2410C", label: "Extração Indicada" },
    "Ausente":           { cor: "#CBD5E1", corBorda: "#94A3B8", label: "Ausente / Extraído" },
    "Implante":          { cor: "#8B5CF6", corBorda: "#6D28D9", label: "Implante" },
    "Selante":           { cor: "#06B6D4", corBorda: "#0E7490", label: "Selante" },
};

const STATUS_LABEL_MAP = {
    "Higido": "Hígido", "Carie": "Cárie", "Restaurado": "Restaurado", "Coroa": "Coroa",
    "Extracao Indicada": "Extração Indicada", "Ausente": "Ausente",
    "Implante": "Implante", "Selante": "Selante",
};

function normalizarStatus(s) {
    if (!s) return "Higido";
    const map = {
        "Hígido": "Higido", "Higido": "Higido", "Cárie": "Carie", "Carie": "Carie",
        "Restaurado": "Restaurado", "Coroa": "Coroa",
        "Extração Indicada": "Extracao Indicada", "Extracao Indicada": "Extracao Indicada",
        "Ausente": "Ausente", "Implante": "Implante", "Selante": "Selante",
    };
    return map[s] || "Higido";
}

/* Estados que se aplicam ao DENTE INTEIRO e que DOMINAM as faces */
const DOMINANTES = ["Ausente", "Implante", "Coroa", "Extracao Indicada"];
/* Estados disponíveis como "dente inteiro" no painel */
const ESTADOS_DENTE = ["Higido", "Coroa", "Extracao Indicada", "Ausente", "Implante"];
/* Subconjunto que faz sentido marcar POR FACE */
const ESTADOS_FACE = ["Carie", "Restaurado", "Selante"];

/* ------------------------------------------------------------------ */
/* Faces (chaves ANATÔMICAS fixas — orientação resolvida só no render) */
/* ------------------------------------------------------------------ */
const FACE_LABEL = {
    mesial: "Mesial",
    distal: "Distal",
    vestibular: "Vestibular",
    lingual: "Lingual / Palatina",
    centro: "Oclusal / Incisal",
};

/* Geometria do quadrado de 5 zonas (cata-vento), viewBox 0 0 100 100 */
const ZONA_PATHS = {
    topo:     "M0 0 L100 0 L67 33 L33 33 Z",
    baixo:    "M0 100 L100 100 L67 67 L33 67 Z",
    esquerda: "M0 0 L33 33 L33 67 L0 100 Z",
    direita:  "M100 0 L67 33 L67 67 L100 100 Z",
    centro:   "M33 33 L67 33 L67 67 L33 67 Z",
};
const ZONAS = ["topo", "baixo", "esquerda", "direita", "centro"];

/* Mapeia cada ZONA visual -> FACE anatômica conforme o quadrante FDI.
   - vestibular fica "para fora da boca": topo na arcada superior (Q1/Q2),
     baixo na inferior (Q3/Q4).
   - mesial aponta à linha média: à direita do quadrado em Q1/Q4 (lado
     esquerdo da tela), à esquerda em Q2/Q3. */
function zonasDoDente(numero) {
    const q = Math.floor(numero / 10);
    const vestibularEmCima = q === 1 || q === 2;
    const mesialNaDireita = q === 1 || q === 4;
    return {
        topo: vestibularEmCima ? "vestibular" : "lingual",
        baixo: vestibularEmCima ? "lingual" : "vestibular",
        direita: mesialNaDireita ? "mesial" : "distal",
        esquerda: mesialNaDireita ? "distal" : "mesial",
        centro: "centro",
    };
}

/* ------------------------------------------------------------------ */
/* Numeração FDI                                                       */
/* ------------------------------------------------------------------ */
const ARCADA_SUPERIOR = [18, 17, 16, 15, 14, 13, 12, 11, 21, 22, 23, 24, 25, 26, 27, 28];
const ARCADA_INFERIOR = [48, 47, 46, 45, 44, 43, 42, 41, 31, 32, 33, 34, 35, 36, 37, 38];

function tipoDente(numero) {
    const d = numero % 10;
    if (d <= 2) return "incisivo";
    if (d === 3) return "canino";
    if (d <= 5) return "premolar";
    return "molar";
}
const NOME_TIPO = { incisivo: "Incisivo", canino: "Canino", premolar: "Pré-molar", molar: "Molar" };

/* "centro" é oclusal em posteriores, incisal em anteriores */
function labelCentro(numero) {
    const t = tipoDente(numero);
    return t === "incisivo" || t === "canino" ? "Incisal" : "Oclusal";
}
function labelFace(numero, faceKey) {
    return faceKey === "centro" ? labelCentro(numero) : FACE_LABEL[faceKey];
}

/* ------------------------------------------------------------------ */
/* Precedência de cor                                                  */
/* ------------------------------------------------------------------ */
/* Estado (key) que vale para uma zona, aplicando a precedência. */
function keyDeZona(dado, faceKey) {
    const status = normalizarStatus(dado.status);
    if (DOMINANTES.includes(status)) return status;
    const faces = dado.faces || {};
    if (faces[faceKey]) return normalizarStatus(faces[faceKey]);
    // Estado de dente inteiro não-dominante (Restaurado/Cárie/Selante, inclusive
    // dados legados) pinta o dente todo quando não há marcação por face.
    if (status !== "Higido" && STATUS[status]) return status;
    return "Higido";
}

function corDeZona(dado, faceKey) {
    return STATUS[keyDeZona(dado, faceKey)] || STATUS.Higido;
}

/* Mapa estado -> id do gradiente de preenchimento (defs únicos, ver OdontogramaDefs) */
const FILL_ID = {
    "Higido": "od-fill-higido",
    "Carie": "od-fill-carie",
    "Restaurado": "od-fill-restaurado",
    "Selante": "od-fill-selante",
    "Coroa": "od-fill-coroa",
    "Extracao Indicada": "od-fill-extracao",
    "Ausente": "od-fill-ausente",
    "Implante": "od-fill-implante",
};

/* Cor de resumo (badge no número) — face mais grave ou estado do dente */
function corResumoDente(dado) {
    const status = normalizarStatus(dado.status);
    if (DOMINANTES.includes(status)) return STATUS[status].cor;
    const faces = dado.faces || {};
    for (const p of ["Carie", "Restaurado", "Selante"]) {
        if (Object.values(faces).some((v) => normalizarStatus(v) === p)) return STATUS[p].cor;
    }
    if (status !== "Higido" && STATUS[status]) return STATUS[status].cor;
    return null; // sem marcação relevante
}

/* Definições SVG compartilhadas (gradientes/clip) — renderizadas UMA vez.
   Dão profundidade de esmalte sem filtro por dente (escala p/ 32 dentes). */
function OdontogramaDefs() {
    const fills = [
        ["od-fill-higido", "#FBF7EE", "#F4EFE3", "#E7DCC4"],
        ["od-fill-carie", "#F87171", "#EF4444", "#C42F2F"],
        ["od-fill-restaurado", "#1597B5", "#0E7490", "#0A5567"],
        ["od-fill-selante", "#38D2EC", "#06B6D4", "#0791A8"],
        ["od-fill-coroa", "#FBC04E", "#F59E0B", "#CC8208"],
        ["od-fill-extracao", "#FB9851", "#F97316", "#D45D0E"],
        ["od-fill-ausente", "#E2E8F0", "#CBD5E1", "#B2BECE"],
        ["od-fill-implante", "#A78BFA", "#8B5CF6", "#6D38D6"],
    ];
    return (
        <svg width={0} height={0} style={{ position: "absolute" }} aria-hidden="true">
            <defs>
                <clipPath id="od-tooth-clip" clipPathUnits="userSpaceOnUse">
                    <rect x="1" y="1" width="98" height="98" rx="14" ry="14" />
                </clipPath>
                {fills.map(([id, claro, base, escuro]) => (
                    <radialGradient key={id} id={id} cx="38%" cy="32%" r="85%">
                        <stop offset="0%" stopColor={claro} />
                        <stop offset="55%" stopColor={base} />
                        <stop offset="100%" stopColor={escuro} />
                    </radialGradient>
                ))}
                <linearGradient id="od-bevel" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#FFFFFF" stopOpacity="0.85" />
                    <stop offset="100%" stopColor="#FFFFFF" stopOpacity="0" />
                </linearGradient>
                <linearGradient id="od-mesa" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#FFFFFF" stopOpacity="0.5" />
                    <stop offset="100%" stopColor="#FFFFFF" stopOpacity="0.06" />
                </linearGradient>
                <radialGradient id="od-inner" cx="50%" cy="46%" r="62%">
                    <stop offset="0%" stopColor="#000000" stopOpacity="0" />
                    <stop offset="78%" stopColor="#000000" stopOpacity="0" />
                    <stop offset="100%" stopColor="#000000" stopOpacity="0.16" />
                </radialGradient>
            </defs>
        </svg>
    );
}

/* ------------------------------------------------------------------ */
/* Forma anatômica (preservada — usada como preview no painel)          */
/* ------------------------------------------------------------------ */
const FORMAS = {
    incisivo: { coroa: "M18 11 Q18 5 28 5 Q38 5 38 11 L40 45 Q40 53 28 53 Q16 53 16 45 Z", raizes: ["M21 50 Q19 75 28 89 Q37 75 35 50 Z"] },
    canino:   { coroa: "M17 13 Q17 5 28 5 Q39 5 39 13 L37 41 Q28 57 19 41 Z", raizes: ["M21 47 Q18 77 28 91 Q38 77 35 47 Z"] },
    premolar: { coroa: "M13 15 Q13 6 28 6 Q43 6 43 15 L43 43 Q37 51 28 45 Q19 51 13 43 Z", raizes: ["M20 45 Q17 73 28 87 Q39 73 36 45 Z"] },
    molar:    { coroa: "M8 17 Q8 7 28 7 Q48 7 48 17 L48 43 Q43 50 38 45 Q33 50 28 45 Q23 50 18 45 Q13 50 8 43 Z", raizes: ["M16 43 Q11 67 16 81 Q22 69 24 43 Z", "M32 43 Q34 69 40 81 Q45 67 40 43 Z"] },
};

function DenteSVG({ tipo, statusKey, tamanho = 40 }) {
    const f = FORMAS[tipo] || FORMAS.molar;
    const st = STATUS[statusKey] || STATUS.Higido;
    const ausente = statusKey === "Ausente";
    return (
        <svg width={tamanho} height={tamanho * 92 / 56} viewBox="0 0 56 92" style={{ display: "block", overflow: "visible", opacity: ausente ? 0.4 : 1 }}>
            {f.raizes.map((d, i) => (
                <path key={i} d={d} fill="#EFE3C9" stroke="#D6C49E" strokeWidth="1.6" strokeLinejoin="round" />
            ))}
            <path d={f.coroa} fill={st.cor} stroke={st.corBorda} strokeWidth="1.6" strokeLinejoin="round" />
            <ellipse cx="21" cy="19" rx="8" ry="5.4" fill="#FFFFFF" opacity={st.claro ? 0.75 : 0.42} />
            <ellipse cx="32" cy="24" rx="4" ry="2.6" fill="#FFFFFF" opacity={st.claro ? 0.5 : 0.22} />
        </svg>
    );
}

/* ------------------------------------------------------------------ */
/* Grade de 5 zonas de um dente                                        */
/* ------------------------------------------------------------------ */
function GradeDente({ numero, dado, tamanho = 38, readOnly, onZonaClick, faceFoco, mostrarMD }) {
    const zonas = zonasDoDente(numero);
    const status = normalizarStatus(dado.status);
    const ausente = status === "Ausente";
    const extracao = status === "Extracao Indicada";
    const implante = status === "Implante";

    // Estado predominante do dente — controla quanto brilho (esmalte) aplicar.
    // Só "Hígido" recebe o realce máximo; dente marcado reduz o branco para a
    // cor-sinal dominar (a profundidade nunca falseia o diagnóstico).
    const resumoKey = (() => {
        if (DOMINANTES.includes(status)) return status;
        const faces = dado.faces || {};
        for (const p of ["Carie", "Restaurado", "Selante"]) {
            if (Object.values(faces).some((v) => normalizarStatus(v) === p)) return p;
        }
        if (status !== "Higido" && STATUS[status]) return status;
        return "Higido";
    })();
    const estadoClaro = resumoKey === "Higido";
    const centroClaro = keyDeZona(dado, "centro") === "Higido";

    return (
        <svg width={tamanho} height={tamanho} viewBox="0 0 100 100" style={{ display: "block", overflow: "visible", opacity: ausente ? 0.5 : 1 }}>
            <g clipPath="url(#od-tooth-clip)">
                {ZONAS.map((z) => {
                    const faceKey = zonas[z];
                    const key = keyDeZona(dado, faceKey);
                    const st = STATUS[key];
                    const marcada = key !== "Higido";
                    const focado = faceFoco === faceKey;
                    return (
                        <path
                            key={z}
                            d={ZONA_PATHS[z]}
                            fill={`url(#${FILL_ID[key] || "od-fill-higido"})`}
                            stroke={focado ? "#155E75" : (marcada ? st.corBorda : "#E2E8F0")}
                            strokeWidth={focado ? 3 : (marcada ? 1.25 : 1)}
                            strokeLinejoin="round"
                            role={readOnly ? undefined : "button"}
                            aria-label={readOnly ? undefined : `Dente ${numero}, face ${labelFace(numero, faceKey)}`}
                            style={{ cursor: readOnly ? "default" : "pointer", paintOrder: focado ? "stroke" : undefined }}
                            onClick={readOnly ? undefined : (e) => { e.stopPropagation(); onZonaClick && onZonaClick(faceKey); }}
                        >
                            <title>{`Dente ${numero} — ${labelFace(numero, faceKey)}: ${st.label}`}</title>
                        </path>
                    );
                })}

                {/* Profundidade de esmalte (não captura clique) */}
                <path d="M2 2 H98 V30 Q50 22 2 30 Z" fill="url(#od-bevel)" opacity={estadoClaro ? 0.55 : 0.32} style={{ pointerEvents: "none" }} />
                <rect x="34" y="34" width="32" height="32" rx="4" fill="url(#od-mesa)" opacity={centroClaro ? 1 : 0.4} style={{ pointerEvents: "none" }} />
                <rect x="1" y="1" width="98" height="98" rx="14" fill="url(#od-inner)" style={{ pointerEvents: "none" }} />
                <g stroke="#FFFFFF" strokeOpacity="0.5" strokeWidth="0.9" style={{ pointerEvents: "none" }}>
                    <line x1="33" y1="33" x2="0" y2="0" />
                    <line x1="67" y1="33" x2="100" y2="0" />
                    <line x1="67" y1="67" x2="100" y2="100" />
                    <line x1="33" y1="67" x2="0" y2="100" />
                </g>
            </g>

            {/* aro de acabamento (perímetro arredondado) */}
            <rect x="1" y="1" width="98" height="98" rx="14" fill="none" stroke="#CBD5E1" strokeWidth="1.25" style={{ pointerEvents: "none" }} />

            {/* marcações de dente inteiro */}
            {(ausente || extracao) && (
                <g stroke={extracao ? "#C2410C" : "#64748B"} strokeWidth="6" strokeLinecap="round" style={{ pointerEvents: "none" }}>
                    <line x1="18" y1="18" x2="82" y2="82" />
                    <line x1="82" y1="18" x2="18" y2="82" />
                </g>
            )}
            {implante && <circle cx="50" cy="50" r="13" fill="#FFFFFF" stroke="#6D28D9" strokeWidth="5" style={{ pointerEvents: "none" }} />}

            {/* rótulos M/D ao selecionar — halo branco (paint-order) p/ legibilidade */}
            {mostrarMD && !ausente && (() => {
                const ladoMesial = zonas.direita === "mesial" ? "dir" : "esq";
                return (
                    <g fontSize="13" fontWeight="700" fill="#155E75" fontFamily="var(--font-secondary)" paintOrder="stroke" stroke="#FFFFFF" strokeWidth="2.5" strokeOpacity="0.85" style={{ pointerEvents: "none" }}>
                        <text x={ladoMesial === "dir" ? 88 : 12} y="54" textAnchor="middle">M</text>
                        <text x={ladoMesial === "dir" ? 12 : 88} y="54" textAnchor="middle">D</text>
                    </g>
                );
            })()}
        </svg>
    );
}

/* ------------------------------------------------------------------ */
/* Dente na arcada                                                     */
/* ------------------------------------------------------------------ */
function Dente({ numero, dado, selecionado, indice, superior, readOnly, onZonaClick, onAbrirPainel }) {
    const [hover, setHover] = useState(false);

    const norm = (indice - 7.5) / 7.5;
    const curva = (1 - norm * norm) * 8;
    const deslocamento = superior ? curva : -curva;
    const escala = hover && !readOnly ? 1.08 : selecionado ? 1.05 : 1;
    const resumo = corResumoDente(dado);

    return (
        <div
            onMouseEnter={() => setHover(true)}
            onMouseLeave={() => setHover(false)}
            style={{
                display: "flex",
                flexDirection: superior ? "column" : "column-reverse",
                alignItems: "center",
                gap: "3px",
                transform: `translateY(${deslocamento}px)`,
                flexShrink: 0,
            }}
        >
            <button
                type="button"
                onClick={() => onAbrirPainel(numero)}
                disabled={readOnly}
                title={`Dente ${numero} — abrir ficha`}
                aria-label={`Dente ${numero}, abrir ficha`}
                style={{ display: "flex", alignItems: "center", gap: "4px", cursor: readOnly ? "default" : "pointer", background: "none", border: "none", padding: "0 2px", font: "inherit" }}
            >
                <span style={{ fontFamily: "var(--font-secondary)", fontSize: "10px", fontWeight: 700, color: selecionado ? "var(--PrimaryColorsTheme)" : "var(--TextColor75)" }}>
                    {numero}
                </span>
                {resumo && <span style={{ width: "7px", height: "7px", borderRadius: "999px", background: resumo, display: "inline-block", flexShrink: 0 }} />}
            </button>

            <div style={{
                borderRadius: "8px",
                padding: "2px",
                background: selecionado ? "var(--PrimaryColorsBack)" : "transparent",
                outline: selecionado ? "2px solid var(--PrimaryColorsTheme)" : "2px solid transparent",
                transition: "transform 0.13s ease, background 0.13s ease, filter 0.13s ease, box-shadow 0.13s ease",
                transform: `scale(${escala})`,
                filter: hover && !readOnly ? "brightness(1.04) saturate(1.03)" : "none",
                boxShadow: hover && !readOnly ? "0 4px 12px rgba(21,94,117,0.18)" : "none",
            }}>
                <GradeDente
                    numero={numero}
                    dado={dado}
                    tamanho={42}
                    readOnly={readOnly}
                    onZonaClick={(faceKey) => onZonaClick(numero, faceKey)}
                />
            </div>
        </div>
    );
}

function Arcada({ numeros, superior, dados, selecionado, onZonaClick, onAbrirPainel, readOnly }) {
    return (
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: "5px" }}>
            {numeros.map((num, i) => (
                <div key={num} style={{ display: "flex", alignItems: "center", gap: "5px" }}>
                    {i === 8 && <div style={{ width: "1px", height: "84px", background: "var(--LineColor)", margin: "0 4px" }} />}
                    <Dente
                        numero={num}
                        indice={i}
                        superior={superior}
                        dado={dados[String(num)] || {}}
                        selecionado={selecionado === num}
                        readOnly={readOnly}
                        onZonaClick={onZonaClick}
                        onAbrirPainel={onAbrirPainel}
                    />
                </div>
            ))}
        </div>
    );
}

/* Sugestões de procedimento por estado de face */
const PROCEDIMENTO_SUGERIDO = {
    "Carie": "Restauração",
    "Restaurado": "Manutenção de restauração",
    "Selante": "Aplicação de selante",
    "Coroa": "Coroa / Prótese",
    "Extracao Indicada": "Extração",
    "Ausente": "Implante / Prótese",
    "Implante": "Manutenção de implante",
};

/* ------------------------------------------------------------------ */
/* Painel de edição                                                    */
/* ------------------------------------------------------------------ */
function PainelEdicao({ numero, dadoAtual, onSalvar, onFechar, onAdicionarAoPlano }) {
    const statusBruto = normalizarStatus(dadoAtual.status);
    // Estados por-superfície gravados como "dente inteiro" (dados legados) não
    // são estados de dente inteiro de verdade — tratamos como Hígido aqui.
    const [statusSel, setStatusSel] = useState(ESTADOS_DENTE.includes(statusBruto) ? statusBruto : "Higido");
    const [faces, setFaces] = useState(() => {
        const f = {};
        Object.entries(dadoAtual.faces || {}).forEach(([k, v]) => { f[k] = normalizarStatus(v); });
        // Migra status superfície legado (Cárie/Restaurado/Selante de boca toda,
        // sem faces) para a face central, deixando-o visível e editável.
        if (!ESTADOS_DENTE.includes(statusBruto) && statusBruto !== "Higido" && !Object.keys(f).length) {
            f.centro = statusBruto;
        }
        return f;
    });
    const [obs, setObs] = useState(dadoAtual.obs || "");
    const [faceFoco, setFaceFoco] = useState("centro");

    const dominante = DOMINANTES.includes(statusSel);
    const dadoPreview = { status: STATUS_LABEL_MAP[statusSel], faces };
    const estadoFaceFoco = faces[faceFoco] || "Higido";

    function aplicarNaFace(estadoKey) {
        setFaces((p) => {
            const novo = { ...p };
            if (!estadoKey || estadoKey === "Higido") delete novo[faceFoco];
            else novo[faceFoco] = estadoKey;
            return novo;
        });
    }

    function salvar() {
        onSalvar(numero, statusSel, obs, faces);
    }

    const sugestaoProc = !dominante && faces[faceFoco] ? PROCEDIMENTO_SUGERIDO[faces[faceFoco]]
        : dominante ? PROCEDIMENTO_SUGERIDO[statusSel] : null;

    return (
        <div
            onClick={(e) => { if (e.target === e.currentTarget) onFechar(); }}
            style={{ position: "fixed", inset: 0, background: "rgba(15,23,42,0.45)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000, padding: "1rem" }}
        >
            <div style={{ background: "var(--ThemeColor)", borderRadius: "var(--radius-lg)", width: "560px", maxWidth: "calc(96vw / var(--app-zoom))", maxHeight: "calc(92vh / var(--app-zoom))", overflowY: "auto", boxShadow: "var(--shadow-md)", border: "1px solid var(--LineColor)" }}>
                {/* cabeçalho */}
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "1rem 1.25rem", borderBottom: "1px solid var(--LineColor)" }}>
                    <div>
                        <h3 style={{ margin: 0, color: "var(--TextColor)", fontSize: "17px" }}>Dente {numero}</h3>
                        <span style={{ fontSize: "12px", color: "var(--TextColor75)" }}>{NOME_TIPO[tipoDente(numero)]}</span>
                    </div>
                    <button onClick={onFechar} aria-label="Fechar" style={{ background: "var(--BackColor)", border: "1px solid var(--LineColor)", borderRadius: "8px", width: "32px", height: "32px", cursor: "pointer", color: "var(--TextColor75)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                        <X size={16} strokeWidth={2} />
                    </button>
                </div>

                <div style={{ padding: "1.25rem", display: "flex", flexDirection: "column", gap: "1.1rem" }}>
                    {/* grade grande + preview anatômico */}
                    <div style={{ display: "flex", gap: "1.25rem", alignItems: "center", justifyContent: "center", background: "var(--BackColor)", borderRadius: "var(--radius-md)", border: "1px solid var(--LineColor)", padding: "1.1rem" }}>
                        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "6px" }}>
                            <GradeDente numero={numero} dado={dadoPreview} tamanho={150} readOnly={dominante} faceFoco={dominante ? null : faceFoco} mostrarMD onZonaClick={(f) => setFaceFoco(f)} />
                            <span style={{ fontSize: "11px", color: "var(--TextColor75)" }}>
                                {dominante ? "Faces ocultas pelo estado do dente" : `Editando: ${labelFace(numero, faceFoco)}`}
                            </span>
                        </div>
                        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "4px", opacity: 0.9 }}>
                            <DenteSVG tipo={tipoDente(numero)} statusKey={dominante ? statusSel : "Higido"} tamanho={64} />
                            <span style={{ fontSize: "10px", color: "var(--TextColor75)" }}>referência</span>
                        </div>
                    </div>

                    {/* estado por face */}
                    <div style={{ opacity: dominante ? 0.45 : 1, pointerEvents: dominante ? "none" : "auto" }}>
                        <p style={{ margin: "0 0 8px 0", fontWeight: 700, fontSize: "12px", color: "var(--TextColor75)", textTransform: "uppercase", letterSpacing: "0.04em" }}>
                            Estado da face — {labelFace(numero, faceFoco)}
                        </p>
                        <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                            {["Higido", ...ESTADOS_FACE].map((key) => {
                                const ativo = estadoFaceFoco === key;
                                const st = STATUS[key];
                                return (
                                    <button key={key} type="button" onClick={() => aplicarNaFace(key)}
                                        style={{ display: "flex", alignItems: "center", gap: "7px", padding: "8px 12px", borderRadius: "8px", cursor: "pointer", background: ativo ? "var(--PrimaryColorsBack)" : "var(--ThemeColor)", border: `1px solid ${ativo ? "var(--PrimaryColorsTheme)" : "var(--LineColor)"}`, fontSize: "12px", fontWeight: ativo ? 700 : 500, color: "var(--TextColor)" }}>
                                        <span style={{ width: "13px", height: "13px", borderRadius: "4px", background: st.cor, border: "1px solid rgba(15,23,42,0.15)", flexShrink: 0 }} />
                                        {key === "Higido" ? "Limpar face" : st.label}
                                    </button>
                                );
                            })}
                        </div>
                    </div>

                    {/* estado do dente inteiro */}
                    <div>
                        <p style={{ margin: "0 0 8px 0", fontWeight: 700, fontSize: "12px", color: "var(--TextColor75)", textTransform: "uppercase", letterSpacing: "0.04em" }}>
                            Estado do dente inteiro
                        </p>
                        <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                            {ESTADOS_DENTE.map((key) => {
                                const ativo = statusSel === key;
                                const st = STATUS[key];
                                return (
                                    <button key={key} type="button" onClick={() => setStatusSel(key)}
                                        style={{ display: "flex", alignItems: "center", gap: "7px", padding: "8px 12px", borderRadius: "8px", cursor: "pointer", background: ativo ? "var(--PrimaryColorsBack)" : "var(--ThemeColor)", border: `1px solid ${ativo ? "var(--PrimaryColorsTheme)" : "var(--LineColor)"}`, fontSize: "12px", fontWeight: ativo ? 700 : 500, color: "var(--TextColor)" }}>
                                        <span style={{ width: "13px", height: "13px", borderRadius: "4px", background: st.cor, border: "1px solid rgba(15,23,42,0.15)", flexShrink: 0 }} />
                                        {key === "Higido" ? "Hígido / por face" : st.label}
                                    </button>
                                );
                            })}
                        </div>
                        {dominante && (
                            <p style={{ margin: "8px 0 0 0", fontSize: "12px", color: "var(--TextColor75)" }}>
                                As marcações por face ficam guardadas e voltam a aparecer ao escolher “Hígido / por face”.
                            </p>
                        )}
                    </div>

                    {/* observação */}
                    <div>
                        <p style={{ margin: "0 0 6px 0", fontWeight: 700, fontSize: "12px", color: "var(--TextColor75)", textTransform: "uppercase", letterSpacing: "0.04em" }}>Observação</p>
                        <textarea value={obs} onChange={(e) => setObs(e.target.value)} rows={2} placeholder="Anotações clínicas sobre este dente..."
                            style={{ width: "100%", padding: "10px 12px", borderRadius: "8px", border: "1px solid var(--LineColor)", fontSize: "14px", resize: "vertical", fontFamily: "inherit", boxSizing: "border-box" }} />
                    </div>

                    {/* ações */}
                    <div style={{ display: "flex", gap: "0.6rem" }}>
                        <button onClick={onFechar} style={{ padding: "11px 16px", background: "var(--BackColor)", color: "var(--TextColor)", border: "1px solid var(--LineColor)", borderRadius: "8px", fontWeight: 600, fontSize: "14px", cursor: "pointer" }}>Cancelar</button>
                        <button onClick={salvar} style={{ flex: 1, padding: "11px", background: "var(--PrimaryColorsTheme)", color: "white", border: "none", borderRadius: "8px", fontWeight: 700, fontSize: "14px", cursor: "pointer" }}>Salvar Dente</button>
                    </div>

                    {sugestaoProc && onAdicionarAoPlano && (
                        <button
                            onClick={() => onAdicionarAoPlano(numero, sugestaoProc, dominante ? null : faceFoco)}
                            style={{ padding: "10px 14px", background: "var(--PrimaryColorsBack)", color: "var(--PrimaryColorsTheme)", border: "1px dashed var(--PrimaryColorsTheme)", borderRadius: "8px", fontWeight: 600, fontSize: "13px", cursor: "pointer" }}
                        >
                            + Adicionar &quot;{sugestaoProc}{!dominante ? ` (${labelFace(numero, faceFoco).toLowerCase()})` : ""}&quot; ao Plano
                        </button>
                    )}
                </div>
            </div>
        </div>
    );
}

/* ------------------------------------------------------------------ */
/* Componente principal                                                */
/* ------------------------------------------------------------------ */
const PINCEIS = [
    { key: "Carie", label: "Cárie" },
    { key: "Restaurado", label: "Restaurado" },
    { key: "Selante", label: "Selante" },
    { key: "Apagar", label: "Apagar" },
];

export default function Odontograma({ dados = {}, onChange, readOnly = false, onAdicionarAoPlano }) {
    const [denteSelecionado, setDenteSelecionado] = useState(null);
    const [pincelAtivo, setPincelAtivo] = useState(null);

    function lerDado(numero) {
        return dados[String(numero)] || {};
    }

    /* clique numa zona da arcada: com pincel ativo aplica direto; senão abre painel */
    function handleZonaArcada(numero, faceKey) {
        const dado = lerDado(numero);
        const dominante = DOMINANTES.includes(normalizarStatus(dado.status));
        if (!pincelAtivo || dominante) {
            setDenteSelecionado(numero);
            return;
        }
        const faces = {};
        Object.entries(dado.faces || {}).forEach(([k, v]) => { faces[k] = normalizarStatus(v); });
        if (pincelAtivo === "Apagar") delete faces[faceKey];
        else faces[faceKey] = pincelAtivo;
        emitir(numero, { status: dado.status || "Hígido", obs: dado.obs || "", faces });
    }

    function emitir(numero, dadoNormalizado) {
        const limpas = {};
        Object.entries(dadoNormalizado.faces || {}).forEach(([k, v]) => {
            const nk = normalizarStatus(v);
            if (nk && nk !== "Higido") limpas[k] = STATUS_LABEL_MAP[nk] || nk;
        });
        const status = normalizarStatus(dadoNormalizado.status);
        const novo = { status: STATUS_LABEL_MAP[status] || "Hígido", obs: dadoNormalizado.obs || "" };
        if (Object.keys(limpas).length) novo.faces = limpas;
        onChange && onChange({ ...dados, [String(numero)]: novo });
    }

    function handleSalvarPainel(numero, statusKey, obs, faces) {
        emitir(numero, { status: STATUS_LABEL_MAP[statusKey], obs, faces });
        setDenteSelecionado(null);
    }

    function handleAdicionarAoPlano(numero, procedimento, faceKey) {
        if (onAdicionarAoPlano) {
            const sufixo = faceKey ? ` (${labelFace(numero, faceKey).toLowerCase()})` : "";
            onAdicionarAoPlano({ dente: String(numero), procedimento: `${procedimento}${sufixo}` });
        }
        setDenteSelecionado(null);
    }

    return (
        <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
            <OdontogramaDefs />
            {!readOnly && (
                <>
                    <p style={{ margin: 0, fontSize: "13px", color: "var(--TextColor75)" }}>
                        Escolha um <strong style={{ color: "var(--TextColor)" }}>pincel</strong> e clique nas faces do dente, ou clique no número para abrir a ficha completa. Não esqueça de clicar em <strong style={{ color: "var(--TextColor)" }}>Salvar Odontograma</strong> ao terminar.
                    </p>
                    {/* rack de pincéis */}
                    <div style={{ display: "flex", flexWrap: "wrap", gap: "8px", alignItems: "center" }}>
                        {PINCEIS.map((p) => {
                            const ativo = pincelAtivo === p.key;
                            const cor = p.key === "Apagar" ? "#94A3B8" : STATUS[p.key].cor;
                            return (
                                <button key={p.key} type="button" onClick={() => setPincelAtivo(ativo ? null : p.key)}
                                    style={{ display: "flex", alignItems: "center", gap: "7px", padding: "7px 14px", borderRadius: "999px", cursor: "pointer", background: ativo ? "var(--PrimaryColorsBack)" : "var(--ThemeColor)", border: `1px solid ${ativo ? "var(--PrimaryColorsTheme)" : "var(--LineColor)"}`, fontSize: "13px", fontWeight: ativo ? 700 : 500, color: "var(--TextColor)" }}>
                                    <span style={{ width: "13px", height: "13px", borderRadius: "4px", background: cor, border: "1px solid rgba(15,23,42,0.15)", flexShrink: 0 }} />
                                    {p.label}
                                </button>
                            );
                        })}
                        <span style={{ fontSize: "12px", color: "var(--TextColor75)", marginLeft: "4px" }}>
                            {pincelAtivo ? `Pincel ativo: ${pincelAtivo === "Apagar" ? "Apagar" : STATUS[pincelAtivo].label}` : "Nenhum pincel — clique abre a ficha"}
                        </span>
                    </div>
                </>
            )}

            {/* mapa dental */}
            <div style={{ background: "var(--ThemeColor)", borderRadius: "var(--radius-lg)", border: "1px solid var(--LineColor)", boxShadow: "var(--shadow-sm)", padding: "1.75rem 1rem", overflowX: "auto" }}>
                <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "6px", minWidth: "820px", margin: "0 auto", width: "fit-content" }}>
                    <span style={{ fontSize: "11px", fontWeight: 700, color: "var(--TextColor75)", textTransform: "uppercase", letterSpacing: "0.06em" }}>Arcada Superior</span>
                    <Arcada numeros={ARCADA_SUPERIOR} superior dados={dados} selecionado={denteSelecionado} onZonaClick={handleZonaArcada} onAbrirPainel={setDenteSelecionado} readOnly={readOnly} />

                    <div style={{ display: "flex", alignItems: "center", gap: "10px", width: "100%", margin: "10px 0", color: "var(--TextColor75)" }}>
                        <div style={{ flex: 1, height: "1px", background: "var(--LineColor)" }} />
                        <span style={{ fontSize: "10px", fontWeight: 600, whiteSpace: "nowrap" }}>LINHA MÉDIA</span>
                        <div style={{ flex: 1, height: "1px", background: "var(--LineColor)" }} />
                    </div>

                    <Arcada numeros={ARCADA_INFERIOR} superior={false} dados={dados} selecionado={denteSelecionado} onZonaClick={handleZonaArcada} onAbrirPainel={setDenteSelecionado} readOnly={readOnly} />
                    <span style={{ fontSize: "11px", fontWeight: 700, color: "var(--TextColor75)", textTransform: "uppercase", letterSpacing: "0.06em", marginTop: "4px" }}>Arcada Inferior</span>
                </div>
            </div>

            {/* legenda */}
            <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
                {Object.entries(STATUS).map(([key, { cor, label }]) => (
                    <div key={key} style={{ display: "flex", alignItems: "center", gap: "6px", background: "var(--ThemeColor)", border: "1px solid var(--LineColor)", borderRadius: "999px", padding: "4px 10px" }}>
                        <span style={{ width: "12px", height: "12px", borderRadius: "3px", background: cor, border: "1px solid rgba(15,23,42,0.15)", flexShrink: 0 }} />
                        <span style={{ fontSize: "12px", color: "var(--TextColor75)", whiteSpace: "nowrap" }}>{label}</span>
                    </div>
                ))}
            </div>

            {denteSelecionado !== null && !readOnly && (
                <PainelEdicao
                    numero={denteSelecionado}
                    dadoAtual={lerDado(denteSelecionado)}
                    onSalvar={handleSalvarPainel}
                    onFechar={() => setDenteSelecionado(null)}
                    onAdicionarAoPlano={onAdicionarAoPlano ? handleAdicionarAoPlano : null}
                />
            )}
        </div>
    );
}

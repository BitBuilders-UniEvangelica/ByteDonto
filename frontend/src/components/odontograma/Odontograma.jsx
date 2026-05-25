import { useState } from "react";
import { X } from "lucide-react";

/* ------------------------------------------------------------------ */
/* Estados clínicos possíveis para cada dente                          */
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

/* ------------------------------------------------------------------ */
/* Numeração FDI — linhas alinhadas anatomicamente                     */
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

const NOME_TIPO = {
    incisivo: "Incisivo", canino: "Canino", premolar: "Pré-molar", molar: "Molar",
};

/* Formato anatômico de cada tipo de dente (coroa no topo, raízes embaixo) */
const FORMAS = {
    incisivo: {
        coroa: "M18 11 Q18 5 28 5 Q38 5 38 11 L40 45 Q40 53 28 53 Q16 53 16 45 Z",
        raizes: ["M21 50 Q19 75 28 89 Q37 75 35 50 Z"],
    },
    canino: {
        coroa: "M17 13 Q17 5 28 5 Q39 5 39 13 L37 41 Q28 57 19 41 Z",
        raizes: ["M21 47 Q18 77 28 91 Q38 77 35 47 Z"],
    },
    premolar: {
        coroa: "M13 15 Q13 6 28 6 Q43 6 43 15 L43 43 Q37 51 28 45 Q19 51 13 43 Z",
        raizes: ["M20 45 Q17 73 28 87 Q39 73 36 45 Z"],
    },
    molar: {
        coroa: "M8 17 Q8 7 28 7 Q48 7 48 17 L48 43 Q43 50 38 45 Q33 50 28 45 Q23 50 18 45 Q13 50 8 43 Z",
        raizes: ["M16 43 Q11 67 16 81 Q22 69 24 43 Z", "M32 43 Q34 69 40 81 Q45 67 40 43 Z"],
    },
};

/* ------------------------------------------------------------------ */
/* Desenho SVG de um dente — coroa no topo, raízes embaixo             */
/* ------------------------------------------------------------------ */
function DenteSVG({ tipo, statusKey, tamanho = 40 }) {
    const f = FORMAS[tipo] || FORMAS.molar;
    const st = STATUS[statusKey] || STATUS.Higido;
    const ausente = statusKey === "Ausente";

    return (
        <svg
            width={tamanho}
            height={tamanho * 92 / 56}
            viewBox="0 0 56 92"
            style={{ display: "block", overflow: "visible", opacity: ausente ? 0.4 : 1 }}
        >
            {/* raízes */}
            {f.raizes.map((d, i) => (
                <path key={i} d={d} fill="#EFE3C9" stroke="#D6C49E" strokeWidth="1.6" strokeLinejoin="round" />
            ))}
            {/* coroa */}
            <path d={f.coroa} fill={st.cor} stroke={st.corBorda} strokeWidth="1.6" strokeLinejoin="round" />
            {/* brilho — dá aparência tridimensional */}
            <ellipse cx="21" cy="19" rx="8" ry="5.4" fill="#FFFFFF" opacity={st.claro ? 0.75 : 0.42} />
            <ellipse cx="32" cy="24" rx="4" ry="2.6" fill="#FFFFFF" opacity={st.claro ? 0.5 : 0.22} />
        </svg>
    );
}

/* ------------------------------------------------------------------ */
/* Um dente clicável dentro da arcada                                  */
/* ------------------------------------------------------------------ */
function Dente({ numero, statusKey, selecionado, onClick, readOnly, superior, indice }) {
    const [hover, setHover] = useState(false);
    const st = STATUS[statusKey] || STATUS.Higido;

    // curva suave da arcada (dentes do meio mais próximos da linha oclusal)
    const norm = (indice - 7.5) / 7.5;
    const curva = (1 - norm * norm) * 8;
    const deslocamento = superior ? curva : -curva;

    const escala = hover && !readOnly ? 1.1 : selecionado ? 1.06 : 1;

    return (
        <div
            onClick={() => !readOnly && onClick(numero)}
            onMouseEnter={() => setHover(true)}
            onMouseLeave={() => setHover(false)}
            title={`Dente ${numero} — ${st.label}`}
            style={{
                display: "flex",
                flexDirection: superior ? "column" : "column-reverse",
                alignItems: "center",
                gap: "3px",
                cursor: readOnly ? "default" : "pointer",
                transform: `translateY(${deslocamento}px)`,
                flexShrink: 0,
            }}
        >
            <span style={{
                fontFamily: "var(--font-secondary)",
                fontSize: "10px",
                fontWeight: 700,
                color: selecionado ? "var(--PrimaryColorsTheme)" : "var(--TextColor75)",
            }}>
                {numero}
            </span>

            <div style={{
                borderRadius: "999px",
                padding: "3px",
                background: selecionado ? "var(--PrimaryColorsBack)" : "transparent",
                outline: selecionado ? "2px solid var(--PrimaryColorsTheme)" : "2px solid transparent",
                transition: "transform 0.13s ease, background 0.13s ease",
                transform: `scale(${escala})`,
                filter: "drop-shadow(0 3px 4px rgba(15,23,42,0.18))",
            }}>
                <div style={{ transform: superior ? "scaleY(-1)" : "none" }}>
                    <DenteSVG tipo={tipoDente(numero)} statusKey={statusKey} tamanho={38} />
                </div>
            </div>
        </div>
    );
}

/* ------------------------------------------------------------------ */
/* Uma arcada (16 dentes) com a linha de centro                        */
/* ------------------------------------------------------------------ */
function Arcada({ numeros, superior, dados, selecionado, onClickDente, readOnly }) {
    return (
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: "5px" }}>
            {numeros.map((num, i) => (
                <div key={num} style={{ display: "flex", alignItems: "center", gap: "5px" }}>
                    {i === 8 && (
                        <div style={{ width: "1px", height: "96px", background: "var(--LineColor)", margin: "0 4px" }} />
                    )}
                    <Dente
                        numero={num}
                        indice={i}
                        superior={superior}
                        statusKey={normalizarStatus((dados[String(num)] || {}).status)}
                        selecionado={selecionado === num}
                        onClick={onClickDente}
                        readOnly={readOnly}
                    />
                </div>
            ))}
        </div>
    );
}

/* Sugestões de procedimento por status — usadas quando o dentista quer
 * adicionar diretamente do odontograma ao plano de tratamento.
 */
const PROCEDIMENTO_SUGERIDO = {
    "Carie":             "Restauração",
    "Restaurado":        "Manutenção de restauração",
    "Coroa":             "Coroa / Prótese",
    "Extracao Indicada": "Extração",
    "Ausente":           "Implante / Prótese",
    "Implante":          "Manutenção de implante",
    "Selante":           "Aplicação de selante",
};

/* ------------------------------------------------------------------ */
/* Painel lateral de edição do dente selecionado                       */
/* ------------------------------------------------------------------ */
function PainelEdicao({ numero, statusAtual, obsAtual, onSalvar, onFechar, onAdicionarAoPlano }) {
    const [statusSel, setStatusSel] = useState(statusAtual || "Higido");
    const [obs, setObs] = useState(obsAtual || "");
    const sugestao = PROCEDIMENTO_SUGERIDO[statusSel];

    return (
        <div
            onClick={e => { if (e.target === e.currentTarget) onFechar(); }}
            style={{
                position: "fixed", inset: 0, background: "rgba(15,23,42,0.45)",
                display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000,
            }}
        >
            <div style={{
                background: "var(--ThemeColor)", borderRadius: "var(--radius-lg)",
                width: "380px", maxWidth: "92vw", boxShadow: "var(--shadow-md)",
                border: "1px solid var(--LineColor)", overflow: "hidden",
            }}>
                {/* cabeçalho */}
                <div style={{
                    display: "flex", justifyContent: "space-between", alignItems: "center",
                    padding: "1rem 1.25rem", borderBottom: "1px solid var(--LineColor)",
                }}>
                    <div>
                        <h3 style={{ margin: 0, color: "var(--TextColor)", fontSize: "17px" }}>Dente {numero}</h3>
                        <span style={{ fontSize: "12px", color: "var(--TextColor75)" }}>
                            {NOME_TIPO[tipoDente(numero)]}
                        </span>
                    </div>
                    <button onClick={onFechar} aria-label="Fechar" style={{
                        background: "var(--BackColor)", border: "1px solid var(--LineColor)",
                        borderRadius: "8px", width: "32px", height: "32px", cursor: "pointer",
                        color: "var(--TextColor75)", display: "flex", alignItems: "center", justifyContent: "center",
                    }}>
                        <X size={16} strokeWidth={2} />
                    </button>
                </div>

                <div style={{ padding: "1.25rem", display: "flex", flexDirection: "column", gap: "1.1rem" }}>
                    {/* molde grande do dente */}
                    <div style={{
                        display: "flex", justifyContent: "center", alignItems: "center",
                        background: "var(--BackColor)", borderRadius: "var(--radius-md)",
                        border: "1px solid var(--LineColor)", padding: "1.25rem",
                        filter: "drop-shadow(0 6px 10px rgba(15,23,42,0.16))",
                    }}>
                        <DenteSVG tipo={tipoDente(numero)} statusKey={statusSel} tamanho={92} />
                    </div>

                    {/* seleção de estado — chips clicáveis */}
                    <div>
                        <p style={{ margin: "0 0 8px 0", fontWeight: 700, fontSize: "12px", color: "var(--TextColor75)", textTransform: "uppercase", letterSpacing: "0.04em" }}>
                            Estado do dente
                        </p>
                        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "6px" }}>
                            {Object.entries(STATUS).map(([key, { cor, label }]) => {
                                const ativo = statusSel === key;
                                return (
                                    <button
                                        key={key}
                                        type="button"
                                        onClick={() => setStatusSel(key)}
                                        style={{
                                            display: "flex", alignItems: "center", gap: "7px",
                                            padding: "8px 10px", borderRadius: "8px", cursor: "pointer",
                                            background: ativo ? "var(--PrimaryColorsBack)" : "var(--ThemeColor)",
                                            border: `1px solid ${ativo ? "var(--PrimaryColorsTheme)" : "var(--LineColor)"}`,
                                            fontSize: "12px", fontWeight: ativo ? 700 : 500,
                                            color: "var(--TextColor)", textAlign: "left",
                                        }}
                                    >
                                        <span style={{ width: "13px", height: "13px", borderRadius: "4px", background: cor, border: "1px solid rgba(15,23,42,0.15)", flexShrink: 0 }} />
                                        {label}
                                    </button>
                                );
                            })}
                        </div>
                    </div>

                    {/* observação */}
                    <div>
                        <p style={{ margin: "0 0 6px 0", fontWeight: 700, fontSize: "12px", color: "var(--TextColor75)", textTransform: "uppercase", letterSpacing: "0.04em" }}>
                            Observação
                        </p>
                        <textarea
                            value={obs}
                            onChange={e => setObs(e.target.value)}
                            rows={3}
                            placeholder="Anotações clínicas sobre este dente..."
                            style={{
                                width: "100%", padding: "10px 12px", borderRadius: "8px",
                                border: "1px solid var(--LineColor)", fontSize: "14px",
                                resize: "vertical", fontFamily: "inherit", boxSizing: "border-box",
                            }}
                        />
                    </div>

                    {/* ações */}
                    <div style={{ display: "flex", gap: "0.6rem" }}>
                        <button onClick={onFechar} style={{
                            padding: "11px 16px", background: "var(--BackColor)", color: "var(--TextColor)",
                            border: "1px solid var(--LineColor)", borderRadius: "8px",
                            fontWeight: 600, fontSize: "14px", cursor: "pointer",
                        }}>
                            Cancelar
                        </button>
                        <button onClick={() => onSalvar(numero, statusSel, obs)} style={{
                            flex: 1, padding: "11px", background: "var(--PrimaryColorsTheme)", color: "white",
                            border: "none", borderRadius: "8px", fontWeight: 700, fontSize: "14px", cursor: "pointer",
                        }}>
                            Salvar Dente
                        </button>
                    </div>

                    {/* Atalho clínico: vai direto deste dente pro plano de tratamento. */}
                    {sugestao && onAdicionarAoPlano && (
                        <button
                            onClick={() => onAdicionarAoPlano(numero, sugestao)}
                            style={{
                                padding: "10px 14px", background: "var(--PrimaryColorsBack)", color: "var(--PrimaryColorsTheme)",
                                border: "1px dashed var(--PrimaryColorsTheme)", borderRadius: "8px",
                                fontWeight: 600, fontSize: "13px", cursor: "pointer", marginTop: "4px",
                            }}
                        >
                            + Adicionar &quot;{sugestao}&quot; ao Plano de Tratamento
                        </button>
                    )}
                </div>
            </div>
        </div>
    );
}

/* ------------------------------------------------------------------ */
/* Componente principal — Odontograma                                  */
/* ------------------------------------------------------------------ */
export default function Odontograma({ dados = {}, onChange, readOnly = false, onAdicionarAoPlano }) {
    const [denteSelecionado, setDenteSelecionado] = useState(null);

    function handleClickDente(numero) {
        setDenteSelecionado(numero);
    }

    function handleSalvar(numero, statusKey, obs) {
        onChange && onChange({
            ...dados,
            [String(numero)]: { status: STATUS_LABEL_MAP[statusKey] || statusKey, obs },
        });
        setDenteSelecionado(null);
    }

    function handleAdicionarAoPlano(numero, procedimento) {
        if (onAdicionarAoPlano) {
            onAdicionarAoPlano({ dente: String(numero), procedimento });
        }
        setDenteSelecionado(null);
    }

    const denteAtual = denteSelecionado !== null ? (dados[String(denteSelecionado)] || {}) : {};

    return (
        <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
            {!readOnly && (
                <p style={{ margin: 0, fontSize: "13px", color: "var(--TextColor75)" }}>
                    Clique em um dente para registrar o estado clínico. Não esqueça de clicar em
                    {" "}<strong style={{ color: "var(--TextColor)" }}>Salvar Odontograma</strong> ao terminar.
                </p>
            )}

            {/* mapa dental */}
            <div style={{
                background: "var(--ThemeColor)", borderRadius: "var(--radius-lg)",
                border: "1px solid var(--LineColor)", boxShadow: "var(--shadow-sm)",
                padding: "1.75rem 1rem", overflowX: "auto",
            }}>
                <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "4px", minWidth: "760px", margin: "0 auto", width: "fit-content" }}>
                    <span style={{ fontSize: "11px", fontWeight: 700, color: "var(--TextColor75)", textTransform: "uppercase", letterSpacing: "0.06em" }}>
                        Arcada Superior
                    </span>
                    <Arcada
                        numeros={ARCADA_SUPERIOR}
                        superior
                        dados={dados}
                        selecionado={denteSelecionado}
                        onClickDente={handleClickDente}
                        readOnly={readOnly}
                    />

                    <div style={{
                        display: "flex", alignItems: "center", gap: "10px",
                        width: "100%", margin: "10px 0", color: "var(--TextColor75)",
                    }}>
                        <div style={{ flex: 1, height: "1px", background: "var(--LineColor)" }} />
                        <span style={{ fontSize: "10px", fontWeight: 600, whiteSpace: "nowrap" }}>LINHA OCLUSAL</span>
                        <div style={{ flex: 1, height: "1px", background: "var(--LineColor)" }} />
                    </div>

                    <Arcada
                        numeros={ARCADA_INFERIOR}
                        superior={false}
                        dados={dados}
                        selecionado={denteSelecionado}
                        onClickDente={handleClickDente}
                        readOnly={readOnly}
                    />
                    <span style={{ fontSize: "11px", fontWeight: 700, color: "var(--TextColor75)", textTransform: "uppercase", letterSpacing: "0.06em", marginTop: "4px" }}>
                        Arcada Inferior
                    </span>
                </div>
            </div>

            {/* legenda */}
            <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
                {Object.entries(STATUS).map(([key, { cor, label }]) => (
                    <div key={key} style={{
                        display: "flex", alignItems: "center", gap: "6px",
                        background: "var(--ThemeColor)", border: "1px solid var(--LineColor)",
                        borderRadius: "999px", padding: "4px 10px",
                    }}>
                        <span style={{ width: "12px", height: "12px", borderRadius: "3px", background: cor, border: "1px solid rgba(15,23,42,0.15)", flexShrink: 0 }} />
                        <span style={{ fontSize: "12px", color: "var(--TextColor75)", whiteSpace: "nowrap" }}>{label}</span>
                    </div>
                ))}
            </div>

            {denteSelecionado !== null && !readOnly && (
                <PainelEdicao
                    numero={denteSelecionado}
                    statusAtual={normalizarStatus(denteAtual.status)}
                    obsAtual={denteAtual.obs || ""}
                    onSalvar={handleSalvar}
                    onFechar={() => setDenteSelecionado(null)}
                    onAdicionarAoPlano={onAdicionarAoPlano ? handleAdicionarAoPlano : null}
                />
            )}
        </div>
    );
}

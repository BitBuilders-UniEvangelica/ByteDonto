import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, Stethoscope, Syringe, ShieldAlert } from "lucide-react";
import { classificarASA, calcularDoseAnestesico, calcularIMC, ANESTESICOS, ASA_DESCRICAO, ROMANO } from "../../utils/clinico";

/* Banner fixo: o cálculo é de apoio; a decisão é do cirurgião-dentista. */
function AvisoResponsabilidade() {
    return (
        <div style={{ display: "flex", gap: "10px", alignItems: "flex-start", background: "var(--WarningBack)", border: "1px solid var(--WarningText)", color: "var(--WarningText)", padding: "12px 14px", borderRadius: "10px", marginBottom: "1.5rem" }}>
            <ShieldAlert size={18} strokeWidth={2.2} style={{ flexShrink: 0, marginTop: "1px" }} />
            <p style={{ margin: 0, fontSize: "13px", lineHeight: 1.5 }}>
                <strong>Cálculo de apoio.</strong> A classificação ASA e a dose de anestésico são sugestões automáticas. A avaliação e a decisão final são de responsabilidade do cirurgião-dentista.
            </p>
        </div>
    );
}

export default function PainelClinico({ anamnese = {}, idade = null, asaManual = "", onAsaChange }) {
    const sugestaoASA = useMemo(() => classificarASA(anamnese), [anamnese]);
    const imc = calcularIMC(anamnese.peso_kg, anamnese.altura_cm);

    // Estado local da calculadora de dose
    const [pesoCalc, setPesoCalc] = useState("");
    const [anestesico, setAnestesico] = useState("lido2_epi");
    const condTxt = `${anamnese.condicoes || ""} ${anamnese.medicacoes || ""}`.toLowerCase();
    const [cardiopata, setCardiopata] = useState(false);
    const [hepatopata, setHepatopata] = useState(false);
    const [gestante, setGestante] = useState(false);

    // A anamnese chega vazia ({}) e é preenchida depois (fetch/edição). Sem isto,
    // o peso e as condições ficariam "presos" no valor inicial e a dose sairia errada.
    useEffect(() => {
        if (anamnese.peso_kg != null && anamnese.peso_kg !== "") setPesoCalc(String(anamnese.peso_kg));
    }, [anamnese.peso_kg]);

    useEffect(() => {
        setCardiopata(/cardio|infarto|arritmia|angina|marca-?passo|hipertens/.test(condTxt));
        setHepatopata(/hepat|cirrose|fígado|figado/.test(condTxt));
        setGestante(/gestante|grávida|gravida/.test(condTxt));
    }, [condTxt]);

    const resultado = useMemo(
        () => calcularDoseAnestesico(pesoCalc, anestesico, { idade, cardiopata, hepatopata, gestante }),
        [pesoCalc, anestesico, idade, cardiopata, hepatopata, gestante]
    );

    const classeEfetiva = asaManual ? Number(asaManual) : sugestaoASA.classe;

    return (
        <div style={{ marginTop: "2rem", borderTop: "1px solid var(--LineColor)", paddingTop: "2rem" }}>
            <AvisoResponsabilidade />

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem" }}>
                {/* ---------- ASA ---------- */}
                <div style={{ background: "var(--ThemeColor)", border: "1px solid var(--LineColor)", borderRadius: "14px", padding: "1.5rem" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "1rem" }}>
                        <Stethoscope size={18} strokeWidth={2.2} style={{ color: "var(--PrimaryColorsTheme)" }} />
                        <h4 style={{ margin: 0, fontSize: "15px", color: "var(--PrimaryColorsTheme)" }}>Classificação ASA</h4>
                    </div>

                    <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "1rem" }}>
                        <div style={{ width: "54px", height: "54px", borderRadius: "12px", background: "var(--PrimaryColorsBack)", color: "var(--PrimaryColorsTheme)", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 800, fontSize: "20px", flexShrink: 0 }}>
                            {ROMANO[classeEfetiva]}
                        </div>
                        <p style={{ margin: 0, fontSize: "13px", color: "var(--TextColor75)", lineHeight: 1.4 }}>
                            {ASA_DESCRICAO[classeEfetiva]}
                        </p>
                    </div>

                    <p style={{ margin: "0 0 6px 0", fontSize: "12px", fontWeight: 700, color: "var(--TextColor75)" }}>
                        Sugestão automática: ASA {ROMANO[sugestaoASA.classe]}
                    </p>
                    {sugestaoASA.motivos.length > 0 ? (
                        <ul style={{ margin: "0 0 1rem 0", paddingLeft: "18px", fontSize: "12px", color: "var(--TextColor75)" }}>
                            {sugestaoASA.motivos.map((m, i) => <li key={i}>{m}</li>)}
                        </ul>
                    ) : (
                        <p style={{ margin: "0 0 1rem 0", fontSize: "12px", color: "var(--TextColor75)" }}>Sem condições sistêmicas relevantes detectadas.</p>
                    )}

                    <label style={{ display: "block", fontSize: "12px", fontWeight: 700, color: "var(--TextColor75)", marginBottom: "4px" }}>
                        Classificação confirmada pelo dentista
                    </label>
                    <select
                        value={asaManual || ""}
                        onChange={(e) => onAsaChange && onAsaChange(e.target.value)}
                        style={{ width: "100%" }}
                    >
                        <option value="">Usar sugestão (ASA {ROMANO[sugestaoASA.classe]})</option>
                        {[1, 2, 3, 4, 5, 6].map((n) => (
                            <option key={n} value={n}>ASA {ROMANO[n]}</option>
                        ))}
                    </select>
                    <p style={{ margin: "10px 0 0 0", fontSize: "11px", color: "var(--TextColor75)" }}>
                        Base: ASA Physical Status Classification System (American Society of Anesthesiologists, rev. 2020).
                    </p>
                </div>

                {/* ---------- DOSE ANESTÉSICO ---------- */}
                <div style={{ background: "var(--ThemeColor)", border: "1px solid var(--LineColor)", borderRadius: "14px", padding: "1.5rem" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "1rem" }}>
                        <Syringe size={18} strokeWidth={2.2} style={{ color: "var(--PrimaryColorsTheme)" }} />
                        <h4 style={{ margin: 0, fontSize: "15px", color: "var(--PrimaryColorsTheme)" }}>Dose Máxima de Anestésico</h4>
                    </div>

                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px", marginBottom: "10px" }}>
                        <div>
                            <label style={{ display: "block", fontSize: "12px", fontWeight: 700, color: "var(--TextColor75)", marginBottom: "4px" }}>Peso (kg)</label>
                            <input type="number" min="0" step="0.1" value={pesoCalc ?? ""} onChange={(e) => setPesoCalc(e.target.value)} style={{ width: "100%" }} placeholder="Ex: 70" />
                        </div>
                        <div>
                            <label style={{ display: "block", fontSize: "12px", fontWeight: 700, color: "var(--TextColor75)", marginBottom: "4px" }}>Idade</label>
                            <input type="text" value={idade != null ? `${idade} anos` : "—"} readOnly style={{ width: "100%", background: "var(--BackColor)", color: "var(--TextColor75)" }} />
                        </div>
                    </div>

                    <label style={{ display: "block", fontSize: "12px", fontWeight: 700, color: "var(--TextColor75)", marginBottom: "4px" }}>Anestésico</label>
                    <select value={anestesico} onChange={(e) => setAnestesico(e.target.value)} style={{ width: "100%", marginBottom: "10px" }}>
                        {Object.entries(ANESTESICOS).map(([k, v]) => (
                            <option key={k} value={k}>{v.nome}</option>
                        ))}
                    </select>

                    <div style={{ display: "flex", flexWrap: "wrap", gap: "12px", marginBottom: "12px", fontSize: "13px" }}>
                        <label style={{ display: "flex", alignItems: "center", gap: "5px", cursor: "pointer" }}>
                            <input type="checkbox" checked={cardiopata} onChange={(e) => setCardiopata(e.target.checked)} /> Cardiopata
                        </label>
                        <label style={{ display: "flex", alignItems: "center", gap: "5px", cursor: "pointer" }}>
                            <input type="checkbox" checked={hepatopata} onChange={(e) => setHepatopata(e.target.checked)} /> Hepatopata
                        </label>
                        <label style={{ display: "flex", alignItems: "center", gap: "5px", cursor: "pointer" }}>
                            <input type="checkbox" checked={gestante} onChange={(e) => setGestante(e.target.checked)} /> Gestante
                        </label>
                    </div>

                    {resultado.erro ? (
                        <div style={{ background: "var(--BackColor)", border: "1px dashed var(--LineColor)", borderRadius: "10px", padding: "12px", fontSize: "13px", color: "var(--TextColor75)" }}>
                            {resultado.erro}
                        </div>
                    ) : (
                        <div style={{ background: "var(--PrimaryColorsBack)", borderRadius: "10px", padding: "14px" }}>
                            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
                                <p style={{ margin: 0, fontSize: "13px", color: "var(--TextColor75)" }}>Dose máxima na sessão</p>
                                <p style={{ margin: 0, fontWeight: 800, fontSize: "22px", color: "var(--PrimaryColorsTheme)" }}>{resultado.dose_mg} mg</p>
                            </div>
                            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginTop: "4px" }}>
                                <p style={{ margin: 0, fontSize: "13px", color: "var(--TextColor75)" }}>Equivale a até</p>
                                <p style={{ margin: 0, fontWeight: 800, fontSize: "16px", color: "var(--PrimaryColorsTheme)" }}>{resultado.tubetes} tubetes</p>
                            </div>
                            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginTop: "4px", paddingTop: "8px", borderTop: "1px dashed var(--LineColor)" }}>
                                <p style={{ margin: 0, fontSize: "12px", color: "var(--TextColor75)" }}>
                                    Teto máximo absoluto / sessão{resultado.ehCrianca ? " (n/a — paciente pediátrico, só por peso)" : ""}
                                </p>
                                <p style={{ margin: 0, fontWeight: 700, fontSize: "13px", color: resultado.limitadoPorTeto ? "var(--DangerText)" : "var(--TextColor75)" }}>
                                    {resultado.ehCrianca ? "—" : `${resultado.tetoAbsoluto} mg`}
                                </p>
                            </div>
                            <p style={{ margin: "8px 0 0 0", fontSize: "11px", color: "var(--TextColor75)" }}>
                                Base: {resultado.mgKgUsado} mg/kg · tubete de 1,8 mL ({resultado.mgPorTubete} mg) · doses máximas conforme Malamed, <em>Handbook of Local Anesthesia</em>, 7ª ed.
                            </p>
                        </div>
                    )}

                    {!resultado.erro && resultado.avisos.length > 0 && (
                        <ul style={{ margin: "10px 0 0 0", paddingLeft: "18px", fontSize: "12px", color: "var(--DangerText)" }}>
                            {resultado.avisos.map((m, i) => (
                                <li key={i} style={{ marginBottom: "4px", display: "list-item" }}>{m}</li>
                            ))}
                        </ul>
                    )}
                    {!resultado.erro && resultado.restricaoIdade && (
                        <p style={{ margin: "8px 0 0 0", fontSize: "12px", color: "var(--DangerText)", display: "flex", alignItems: "center", gap: "4px" }}>
                            <AlertTriangle size={13} strokeWidth={2.4} /> {resultado.restricaoIdade}
                        </p>
                    )}
                </div>
            </div>
        </div>
    );
}

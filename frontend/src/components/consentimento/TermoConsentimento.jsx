import { useState, useRef, useEffect } from "react";
import { apiUploadImagem } from "../../services/api";
import { Check, X, FileSignature } from "lucide-react";
import { useFeedback } from "../../hooks/useFeedback";

/* Texto padrão dos dois termos. Substituir pela versão validada pelo jurídico
 * da clínica antes de subir pra produção real. */
const TEXTO_LGPD = `Autorizo, nos termos da Lei nº 13.709/2018 (LGPD), o tratamento dos meus dados
pessoais e dados sensíveis de saúde (anamnese, prontuário, imagens, exames e
informações financeiras) pela clínica, exclusivamente para fins de prestação
do serviço odontológico, registro do prontuário (obrigatório por 20 anos
conforme Res. CFO 226/2020), comunicação clínica e cobrança.

Estou ciente de que posso solicitar acesso, correção, anonimização ou
exclusão dos meus dados, observadas as obrigações legais de guarda do
prontuário, mediante contato com a clínica.`;

const TEXTO_PROCEDIMENTO = `Declaro que fui informado(a) pelo cirurgião-dentista sobre o diagnóstico, o
plano de tratamento proposto, alternativas, riscos, contraindicações,
prognóstico e cuidados pós-operatórios. Concedo meu consentimento livre e
esclarecido para a realização dos procedimentos previstos no plano de
tratamento, podendo revogar este consentimento a qualquer tempo, por escrito,
sem prejuízo do tratamento já realizado.`;

/* Imprime + salva como PDF.
 * Estratégia simples: abre uma janela, escreve o HTML formatado, e o
 * usuário usa Ctrl+P / "Salvar como PDF". Funciona em qualquer navegador
 * sem precisar instalar lib pesada de PDF.
 *
 * Para upload, fazemos uma 2ª etapa: gera um Blob HTML com o termo + assinatura
 * em data-url e envia pra galeria como "termo_consentimento". A clínica fica
 * com a prova digital no prontuário do paciente.
 */
function htmlDoTermo({ paciente, tipo, assinaturaDataUrl }) {
    const hoje = new Date().toLocaleDateString("pt-BR");
    const titulo = tipo === "termo_lgpd" ? "Termo de Consentimento – LGPD" : "Termo de Consentimento Informado";
    const corpo = tipo === "termo_lgpd" ? TEXTO_LGPD : TEXTO_PROCEDIMENTO;
    return `<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="utf-8"><title>${titulo}</title>
<style>
    body{font-family:Arial,sans-serif;max-width:700px;margin:32px auto;color:#111;line-height:1.55}
    h1{color:#155E75;border-bottom:2px solid #155E75;padding-bottom:6px;font-size:20px}
    .meta{color:#555;font-size:13px;margin-bottom:24px}
    pre{white-space:pre-wrap;font-family:inherit;font-size:14px}
    .assinatura{margin-top:48px;border-top:1px solid #999;padding-top:8px;text-align:center;font-size:13px;color:#555}
    .assinatura img{max-width:280px;max-height:120px;display:block;margin:0 auto 8px auto}
</style></head>
<body>
    <h1>${titulo}</h1>
    <div class="meta">
        <strong>Paciente:</strong> ${paciente?.nome || "—"}<br/>
        <strong>CPF:</strong> ${paciente?.cpf || "—"}<br/>
        <strong>Data:</strong> ${hoje}
    </div>
    <pre>${corpo}</pre>
    <div class="assinatura">
        ${assinaturaDataUrl ? `<img src="${assinaturaDataUrl}" alt="Assinatura"/>` : ""}
        Assinatura do(a) paciente ou responsável
    </div>
</body></html>`;
}

export default function TermoConsentimento({ paciente, token, onArquivado }) {
    const [tipo, setTipo] = useState("termo_lgpd"); // 'termo_lgpd' | 'termo_consentimento'
    const [aceitou, setAceitou] = useState(false);
    const [salvando, setSalvando] = useState(false);
    const [erro, setErro] = useState("");
    const { toast } = useFeedback();
    const [sucesso, setSucesso] = useState(false);

    // Canvas de assinatura — simples (pointer events)
    const canvasRef = useRef(null);
    const desenhandoRef = useRef(false);

    useEffect(() => {
        const c = canvasRef.current;
        if (!c) return;
        const ctx = c.getContext("2d");
        ctx.lineWidth = 2;
        ctx.lineCap = "round";
        ctx.strokeStyle = "#0f172a";
        ctx.fillStyle = "#ffffff";
        ctx.fillRect(0, 0, c.width, c.height);
    }, [tipo]);

    function pos(e) {
        const c = canvasRef.current;
        const r = c.getBoundingClientRect();
        const x = (e.touches?.[0]?.clientX ?? e.clientX) - r.left;
        const y = (e.touches?.[0]?.clientY ?? e.clientY) - r.top;
        return { x: x * (c.width / r.width), y: y * (c.height / r.height) };
    }

    function inicio(e) { desenhandoRef.current = true; const p = pos(e); const ctx = canvasRef.current.getContext("2d"); ctx.beginPath(); ctx.moveTo(p.x, p.y); }
    function move(e) { if (!desenhandoRef.current) return; e.preventDefault(); const p = pos(e); const ctx = canvasRef.current.getContext("2d"); ctx.lineTo(p.x, p.y); ctx.stroke(); }
    function fim() { desenhandoRef.current = false; }

    function limparAssinatura() {
        const c = canvasRef.current;
        const ctx = c.getContext("2d");
        ctx.fillStyle = "#ffffff";
        ctx.fillRect(0, 0, c.width, c.height);
    }

    function temAssinatura() {
        // Heurística: se algum pixel é não-branco, considera assinada
        const c = canvasRef.current;
        if (!c) return false;
        const ctx = c.getContext("2d");
        const img = ctx.getImageData(0, 0, c.width, c.height);
        for (let i = 0; i < img.data.length; i += 4) {
            if (img.data[i] < 240 || img.data[i + 1] < 240 || img.data[i + 2] < 240) return true;
        }
        return false;
    }

    async function salvarNoProntuario() {
        setErro("");
        if (!aceitou) { setErro("Marque a confirmação de leitura."); return; }
        if (!temAssinatura()) { setErro("Colete a assinatura no quadro abaixo."); return; }
        setSalvando(true);
        try {
            const assinaturaDataUrl = canvasRef.current.toDataURL("image/png");
            const html = htmlDoTermo({ paciente, tipo, assinaturaDataUrl });
            const blob = new Blob([html], { type: "text/html" });
            const tituloArquivo = tipo === "termo_lgpd"
                ? `termo-lgpd-${paciente.id}.html`
                : `termo-consentimento-${paciente.id}.html`;
            const file = new File([blob], tituloArquivo, { type: "text/html" });
            await apiUploadImagem(token, paciente.id, file, tipo);
            setSucesso(true);
            toast({ tipo: "sucesso", titulo: "Termo assinado e arquivado", mensagem: `Salvo nos arquivos de ${paciente.nome}.` });
            setAceitou(false);
            limparAssinatura();
            onArquivado && onArquivado();
        } catch (e) {
            setErro(e.message || "Não foi possível salvar o termo.");
            toast({ tipo: "erro", titulo: "Não foi possível salvar o termo", mensagem: e.message || "Tente novamente em instantes." });
        } finally {
            setSalvando(false);
        }
    }

    function imprimir() {
        if (!temAssinatura()) { setErro("Colete a assinatura no quadro antes de imprimir."); return; }
        const assinaturaDataUrl = canvasRef.current.toDataURL("image/png");
        const html = htmlDoTermo({ paciente, tipo, assinaturaDataUrl });
        const w = window.open("", "_blank", "width=800,height=600");
        w.document.write(html);
        w.document.close();
        w.focus();
        w.print();
    }

    return (
        <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
            <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
                <FileSignature size={20} strokeWidth={2} color="var(--PrimaryColorsTheme)" />
                <h3 style={{ margin: 0, color: "var(--PrimaryColorsTheme)" }}>Termo de Consentimento</h3>
            </div>

            <div style={{ display: "flex", gap: "0.5rem" }}>
                {["termo_lgpd", "termo_consentimento"].map(t => (
                    <button
                        key={t}
                        type="button"
                        onClick={() => { setTipo(t); setSucesso(false); }}
                        style={{
                            padding: "8px 16px", borderRadius: "10px",
                            border: "1px solid var(--LineColor)", cursor: "pointer",
                            background: tipo === t ? "var(--PrimaryColorsTheme)" : "white",
                            color: tipo === t ? "white" : "var(--TextColor75)",
                            fontWeight: 600, fontSize: "13px",
                        }}
                    >
                        {t === "termo_lgpd" ? "LGPD (uso de dados)" : "Procedimento Clínico"}
                    </button>
                ))}
            </div>

            <pre style={{
                whiteSpace: "pre-wrap", fontFamily: "inherit", fontSize: "13px",
                background: "var(--BackColor)", padding: "1rem", borderRadius: "10px",
                border: "1px solid var(--LineColor)", margin: 0, maxHeight: "240px", overflowY: "auto",
            }}>
                {tipo === "termo_lgpd" ? TEXTO_LGPD : TEXTO_PROCEDIMENTO}
            </pre>

            <label style={{ display: "flex", gap: "10px", alignItems: "flex-start", cursor: "pointer", fontSize: "13px" }}>
                <input type="checkbox" checked={aceitou} onChange={e => setAceitou(e.target.checked)} style={{ marginTop: "2px" }} />
                <span style={{ fontSize: "13px", fontWeight: 400, lineHeight: 1.5 }}>Li e concordo com os termos acima. Confirmo que sou o(a) paciente ou responsável legal.</span>
            </label>

            <div>
                <p style={{ margin: "0 0 6px 0", fontWeight: 700, fontSize: "12px", color: "var(--TextColor75)", textTransform: "uppercase" }}>Assinatura</p>
                <canvas
                    ref={canvasRef}
                    width={600}
                    height={160}
                    onPointerDown={inicio}
                    onPointerMove={move}
                    onPointerUp={fim}
                    onPointerLeave={fim}
                    style={{
                        width: "100%", maxWidth: "600px", height: "160px",
                        border: "1px dashed var(--LineColor)", borderRadius: "10px",
                        background: "white", touchAction: "none", display: "block",
                    }}
                />
                <button
                    type="button"
                    onClick={limparAssinatura}
                    style={{ marginTop: "6px", fontSize: "12px", background: "none", border: "none", color: "var(--TextColor75)", cursor: "pointer" }}
                >
                    <X size={12} strokeWidth={2.5} style={{ verticalAlign: "middle" }} /> Limpar assinatura
                </button>
            </div>

            {erro && <p style={{ background: "var(--DangerBack)", color: "var(--DangerText)", padding: "8px 12px", borderRadius: "8px", fontSize: "13px", margin: 0 }}>{erro}</p>}
            {sucesso && (
                <p style={{ background: "var(--SuccessBack)", color: "var(--SuccessText)", padding: "8px 12px", borderRadius: "8px", fontSize: "13px", margin: 0, display: "flex", alignItems: "center", gap: "6px" }}>
                    <Check size={14} strokeWidth={2.5} /> Termo arquivado no prontuário (aba Arquivos &amp; Imagens).
                </p>
            )}

            <div style={{ display: "flex", gap: "0.5rem", justifyContent: "flex-end" }}>
                <button
                    type="button"
                    onClick={imprimir}
                    style={{ padding: "10px 20px", background: "transparent", color: "var(--TextColor75)", border: "1px solid var(--LineColor)", borderRadius: "10px", fontSize: "13px", fontWeight: 600, cursor: "pointer" }}
                >
                    Imprimir / Salvar PDF
                </button>
                <button
                    type="button"
                    onClick={salvarNoProntuario}
                    disabled={salvando}
                    style={{ padding: "10px 24px", background: "var(--PrimaryColorsTheme)", color: "white", border: "none", borderRadius: "10px", fontSize: "13px", fontWeight: 700, cursor: salvando ? "not-allowed" : "pointer", opacity: salvando ? 0.7 : 1 }}
                >
                    {salvando ? "Salvando..." : "Arquivar no Prontuário"}
                </button>
            </div>
        </div>
    );
}

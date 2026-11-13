import { useEffect, useRef, useState } from "react";
import { Camera, RotateCcw, Check } from "lucide-react";
import { formatarDataHora } from "./formatarDataHora";

/* Modal de captura de foto AO VIVO.
 * Usa somente a câmera do dispositivo (getUserMedia) — não existe <input type="file">,
 * então não é possível escolher imagem da galeria ou de arquivos externos.
 * Fluxo: câmera ao vivo → "Tirar foto" → pré-visualização → "Registrar foto" ou "Tirar novamente".
 * Ao registrar, devolve { dataUrl, tiradaEm } (tiradaEm = Date do instante do clique).
 *
 * Obs.: navegadores só liberam a câmera em contexto seguro (https ou localhost). */
export default function CapturaFoto({ onConfirmar, onFechar }) {
    const videoRef = useRef(null);
    const streamRef = useRef(null);
    const ativoRef = useRef(false); // evita stream "órfão" se o modal fechar antes da câmera abrir
    const [erro, setErro] = useState(() => navigator.mediaDevices?.getUserMedia
        ? ""
        : "Este navegador não permite acesso à câmera (é necessário HTTPS ou localhost).");
    const [pronta, setPronta] = useState(false);
    const [captura, setCaptura] = useState(null); // { dataUrl, tiradaEm }

    function pararCamera() {
        streamRef.current?.getTracks().forEach(t => t.stop());
        streamRef.current = null;
        setPronta(false);
    }

    function mensagemErro(e) {
        if (e?.name === "NotAllowedError") return "Permissão da câmera negada. Libere o acesso nas configurações do navegador.";
        if (e?.name === "NotFoundError" || e?.name === "OverconstrainedError") return "Nenhuma câmera encontrada neste dispositivo.";
        if (e?.name === "NotReadableError") return "A câmera está sendo usada por outro aplicativo.";
        return "Não foi possível abrir a câmera.";
    }

    function iniciarCamera() {
        if (!navigator.mediaDevices?.getUserMedia) return;
        navigator.mediaDevices.getUserMedia({
            video: { facingMode: "user", width: { ideal: 1280 }, height: { ideal: 720 } },
            audio: false,
        }).then(stream => {
            if (!ativoRef.current) { stream.getTracks().forEach(t => t.stop()); return; }
            streamRef.current = stream;
            if (videoRef.current) {
                videoRef.current.srcObject = stream;
                videoRef.current.play().catch(() => {});
            }
        }).catch(e => setErro(mensagemErro(e)));
    }

    useEffect(() => {
        ativoRef.current = true;
        iniciarCamera();
        return () => { ativoRef.current = false; pararCamera(); };
        // eslint-disable-next-line react-hooks/exhaustive-deps -- abre a câmera só ao montar
    }, []);

    useEffect(() => {
        function onKey(e) { if (e.key === "Escape") onFechar(); }
        window.addEventListener("keydown", onKey);
        return () => window.removeEventListener("keydown", onKey);
    }, [onFechar]);

    function tirarFoto() {
        const v = videoRef.current;
        if (!v || !v.videoWidth) return;
        const c = document.createElement("canvas");
        c.width = v.videoWidth;
        c.height = v.videoHeight;
        c.getContext("2d").drawImage(v, 0, 0, c.width, c.height);
        setCaptura({ dataUrl: c.toDataURL("image/jpeg", 0.85), tiradaEm: new Date() });
        pararCamera();
    }

    function tentarNovamente() {
        setErro("");
        iniciarCamera();
    }

    function tirarNovamente() {
        setCaptura(null);
        iniciarCamera();
    }

    function registrar() {
        onConfirmar(captura);
    }

    const btnBase = { padding: "10px 18px", borderRadius: "10px", fontSize: "13px", fontWeight: 600, cursor: "pointer", display: "inline-flex", alignItems: "center", gap: "6px" };
    const btnSecundario = { ...btnBase, background: "transparent", color: "var(--TextColor75)", border: "1px solid var(--LineColor)" };
    const btnPrimario = { ...btnBase, background: "var(--PrimaryColorsTheme)", color: "white", border: "none", fontWeight: 700 };

    return (
        <div
            onClick={e => { if (e.target === e.currentTarget) onFechar(); }}
            style={{ position: "fixed", inset: 0, background: "rgba(15,23,42,0.6)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000, padding: "1rem" }}
        >
            <div role="dialog" aria-modal="true" aria-label="Registrar foto do paciente" style={{ background: "var(--ThemeColor)", borderRadius: "var(--radius-lg)", width: "640px", maxWidth: "100%", maxHeight: "100%", overflowY: "auto", boxShadow: "var(--shadow-md)", border: "1px solid var(--LineColor)" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "1rem 1.25rem", borderBottom: "1px solid var(--LineColor)" }}>
                    <h3 style={{ margin: 0, color: "var(--TextColor)", fontSize: "17px" }}>
                        {captura ? "Confirmar foto" : "Registrar foto"}
                    </h3>
                </div>

                <div style={{ padding: "1.25rem", display: "flex", flexDirection: "column", gap: "1rem" }}>
                    <div style={{ position: "relative", background: "#0f172a", borderRadius: "10px", overflow: "hidden", aspectRatio: "4 / 3", display: "flex", alignItems: "center", justifyContent: "center" }}>
                        {captura ? (
                            <img src={captura.dataUrl} alt="Foto capturada" style={{ width: "100%", height: "100%", objectFit: "contain" }} />
                        ) : (
                            <video
                                ref={videoRef}
                                autoPlay
                                playsInline
                                muted
                                onLoadedMetadata={() => setPronta(true)}
                                // espelhado só na pré-visualização (efeito "espelho"); a foto salva não é espelhada
                                style={{ width: "100%", height: "100%", objectFit: "contain", transform: "scaleX(-1)", display: erro ? "none" : "block" }}
                            />
                        )}
                        {!captura && !pronta && !erro && (
                            <span style={{ position: "absolute", color: "white", fontSize: "13px" }}>Abrindo câmera...</span>
                        )}
                        {erro && (
                            <span style={{ position: "absolute", color: "white", fontSize: "13px", textAlign: "center", padding: "1rem" }}>{erro}</span>
                        )}
                    </div>

                    {captura && (
                        <p style={{ margin: 0, fontSize: "13px", color: "var(--TextColor75)", textAlign: "center" }}>
                            Deseja registrar esta foto? Tirada em {formatarDataHora(captura.tiradaEm)}.
                        </p>
                    )}

                    <div style={{ display: "flex", gap: "0.5rem", justifyContent: "flex-end", flexWrap: "wrap" }}>
                        {captura ? (
                            <>
                                <button type="button" onClick={onFechar} style={btnSecundario}>Cancelar</button>
                                <button type="button" onClick={tirarNovamente} style={btnSecundario}>
                                    <RotateCcw size={14} strokeWidth={2.5} /> Tirar novamente
                                </button>
                                <button type="button" onClick={registrar} style={btnPrimario}>
                                    <Check size={14} strokeWidth={2.5} /> Registrar foto
                                </button>
                            </>
                        ) : (
                            <>
                                <button type="button" onClick={onFechar} style={btnSecundario}>Cancelar</button>
                                {erro ? (
                                    <button type="button" onClick={tentarNovamente} style={btnPrimario}>
                                        <RotateCcw size={14} strokeWidth={2.5} /> Tentar novamente
                                    </button>
                                ) : (
                                    <button type="button" onClick={tirarFoto} disabled={!pronta} style={{ ...btnPrimario, opacity: pronta ? 1 : 0.6, cursor: pronta ? "pointer" : "not-allowed" }}>
                                        <Camera size={14} strokeWidth={2.5} /> Tirar foto
                                    </button>
                                )}
                            </>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}


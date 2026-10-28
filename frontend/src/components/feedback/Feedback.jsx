/* Componentes de feedback do sistema (Figma: "Propostas de melhoria").
   Substituem alert()/confirm() do navegador e os erros silenciosos:
   toast, banner, spinner, bloco carregando, estado de erro e modal de confirmação. */
import { useCallback, useEffect, useRef, useState } from "react";
import { CircleCheck, CircleX, TriangleAlert, Info, X, WifiOff, Trash2, LoaderCircle } from "lucide-react";
import { FeedbackContext } from "../../hooks/useFeedback";
import "../../styles/Feedback.css";

const ICONES_TOAST = { sucesso: CircleCheck, erro: CircleX, aviso: TriangleAlert, info: Info };
const ICONES_BANNER = { conexao: WifiOff, aviso: TriangleAlert, info: Info };
const DURACAO_TOAST_MS = 5000;

/* PROVIDER — fica em volta das rotas e expõe toast() e confirmar(). */
export function FeedbackProvider({ children }) {
    const [toasts, setToasts] = useState([]);
    const [confirmacao, setConfirmacao] = useState(null);
    const proximoId = useRef(0);

    const fecharToast = useCallback((id) => {
        setToasts(lista => lista.filter(t => t.id !== id));
    }, []);

    const toast = useCallback(({ tipo = "sucesso", titulo, mensagem }) => {
        const id = ++proximoId.current;
        setToasts(lista => [...lista, { id, tipo, titulo, mensagem }]);
        setTimeout(() => fecharToast(id), DURACAO_TOAST_MS);
    }, [fecharToast]);

    // Devolve uma Promise<boolean>, como o confirm() nativo, mas com o modal do sistema.
    const confirmar = useCallback(({ titulo, mensagem, acao = "Remover" }) => (
        new Promise(resolve => setConfirmacao({ titulo, mensagem, acao, resolve }))
    ), []);

    function responder(valor) {
        confirmacao?.resolve(valor);
        setConfirmacao(null);
    }

    return (
        <FeedbackContext.Provider value={{ toast, confirmar }}>
            {children}
            <div className="toast-area" role="status" aria-live="polite">
                {toasts.map(t => (
                    <Toast key={t.id} {...t} onFechar={() => fecharToast(t.id)} />
                ))}
            </div>
            {confirmacao && (
                <ModalConfirmacao
                    titulo={confirmacao.titulo}
                    mensagem={confirmacao.mensagem}
                    acao={confirmacao.acao}
                    onCancelar={() => responder(false)}
                    onConfirmar={() => responder(true)}
                />
            )}
        </FeedbackContext.Provider>
    );
}

/* TOAST — canto superior direito, some em 5s. */
export function Toast({ tipo = "sucesso", titulo, mensagem, onFechar }) {
    const Icone = ICONES_TOAST[tipo] || Info;
    return (
        <div className={`toast toast-${tipo}`}>
            <span className="toast-faixa" />
            <span className="toast-icone"><Icone size={18} strokeWidth={2} /></span>
            <div className="toast-texto">
                <p className="toast-titulo">{titulo}</p>
                {mensagem && <p className="toast-mensagem">{mensagem}</p>}
            </div>
            <button type="button" className="toast-fechar" onClick={onFechar} aria-label="Fechar">
                <X size={16} strokeWidth={2} />
            </button>
        </div>
    );
}

/* BANNER — aviso no topo do conteúdo. tipo: "conexao" | "aviso" | "info". */
export function Banner({ tipo = "conexao", texto, onTentarNovamente }) {
    const Icone = ICONES_BANNER[tipo] || Info;
    return (
        <div className={`banner banner-${tipo}`} role="alert">
            <Icone size={20} strokeWidth={2} />
            <p className="banner-texto">{texto}</p>
            {onTentarNovamente && (
                <button type="button" className="btn-feedback btn-feedback-secundario" onClick={onTentarNovamente}>
                    Tentar novamente
                </button>
            )}
        </div>
    );
}

export function Spinner({ tamanho = 40 }) {
    return <LoaderCircle className="spinner" size={tamanho} strokeWidth={2} aria-hidden="true" />;
}

export function BlocoCarregando({ texto = "Carregando..." }) {
    return (
        <div className="bloco-carregando">
            <Spinner />
            <p>{texto}</p>
        </div>
    );
}

/* ESTADO DE ERRO — "conexao" (ícone), "404" (número) ou "nao-encontrado" (só texto). */
export function EstadoErro({ tipo = "conexao", titulo, mensagem, textoBotao, onAcao }) {
    const ehConexao = tipo === "conexao";
    return (
        <div className="estado-erro">
            {ehConexao && <span className="estado-erro-icone"><WifiOff size={32} strokeWidth={2} /></span>}
            {tipo === "404" && <p className="estado-erro-codigo">404</p>}
            <div className="estado-erro-textos">
                <p className="estado-erro-titulo">{titulo || (ehConexao ? "Sem conexão com o servidor" : "Página não encontrada")}</p>
                {mensagem && <p className="estado-erro-mensagem">{mensagem}</p>}
            </div>
            {onAcao && (
                <button type="button" className="btn-feedback btn-feedback-primario" onClick={onAcao}>
                    {textoBotao || "Tentar novamente"}
                </button>
            )}
        </div>
    );
}

/* MODAL DE CONFIRMAÇÃO (exclusão) */
export function ModalConfirmacao({ titulo, mensagem, acao = "Remover", onCancelar, onConfirmar }) {
    useEffect(() => {
        const onKey = (e) => { if (e.key === "Escape") onCancelar(); };
        window.addEventListener("keydown", onKey);
        return () => window.removeEventListener("keydown", onKey);
    }, [onCancelar]);

    return (
        <div className="confirmacao-fundo" onClick={onCancelar}>
            <div className="confirmacao" role="alertdialog" aria-modal="true" onClick={e => e.stopPropagation()}>
                <span className="confirmacao-icone"><Trash2 size={22} strokeWidth={2} /></span>
                <div className="confirmacao-textos">
                    <p className="confirmacao-titulo">{titulo}</p>
                    <p className="confirmacao-mensagem">{mensagem || "Esta ação não pode ser desfeita."}</p>
                </div>
                <div className="confirmacao-acoes">
                    <button type="button" className="btn-feedback btn-feedback-secundario" onClick={onCancelar}>Cancelar</button>
                    <button type="button" className="btn-feedback btn-feedback-destrutivo" onClick={onConfirmar} autoFocus>{acao}</button>
                </div>
            </div>
        </div>
    );
}

/* Mensagem de erro embaixo de um campo de formulário. */
export function ErroCampo({ children }) {
    if (!children) return null;
    return (
        <p className="erro-campo">
            <CircleX size={14} strokeWidth={2} />
            {children}
        </p>
    );
}

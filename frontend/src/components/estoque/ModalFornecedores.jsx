import { useState } from "react";
import { Power } from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import { apiCriarFornecedor, apiAtualizarFornecedor } from "../../services/api";
import { useFeedback } from "../../hooks/useFeedback";
import { formatPhone } from "../../utils/formatters";
import ModalEstoque from "./ModalEstoque";

const VAZIO = { nome: "", cnpj: "", telefone: "", email: "" };

/* Lista os fornecedores ativos e cadastra novos. Fornecedor não é excluído,
   só inativado, para não quebrar o histórico de entradas. */
export default function ModalFornecedores({ fornecedores, onAlterado, onFechar }) {
    const { token } = useAuth();
    const { toast, confirmar } = useFeedback();
    const [form, setForm] = useState(VAZIO);
    const [erro, setErro] = useState("");
    const [salvando, setSalvando] = useState(false);

    const set = (campo) => (e) => setForm(f => ({ ...f, [campo]: e.target.value }));

    async function adicionar() {
        if (!form.nome.trim()) return setErro("Informe o nome do fornecedor.");
        setSalvando(true);
        setErro("");
        try {
            await apiCriarFornecedor(token, form);
            toast({ tipo: "sucesso", titulo: "Fornecedor cadastrado", mensagem: form.nome.trim() });
            setForm(VAZIO);
            onAlterado();
        } catch (e) {
            setErro(e.message);
        } finally {
            setSalvando(false);
        }
    }

    async function inativar(f) {
        const ok = await confirmar({
            titulo: `Inativar ${f.nome}?`,
            mensagem: "Ele deixa de aparecer nas listas. O histórico de entradas é mantido.",
            acao: "Inativar",
        });
        if (!ok) return;
        try {
            await apiAtualizarFornecedor(token, f.id, { ativo: false });
            toast({ tipo: "sucesso", titulo: "Fornecedor inativado", mensagem: f.nome });
            onAlterado();
        } catch (e) {
            toast({ tipo: "erro", titulo: "Não foi possível inativar", mensagem: e.message });
        }
    }

    return (
        <ModalEstoque
            titulo="Fornecedores"
            subtitulo="Empresas de quem a clínica compra materiais e insumos."
            erro={erro}
            salvando={salvando}
            onCancelar={onFechar}
            onSalvar={adicionar}
            textoSalvar="Adicionar fornecedor"
        >
            <div className="est-forn-lista">
                {fornecedores.length === 0 && <p className="est-vazio" style={{ padding: "1rem" }}>Nenhum fornecedor cadastrado.</p>}
                {fornecedores.map(f => (
                    <div key={f.id} className="est-forn-linha">
                        <div style={{ minWidth: 0 }}>
                            <strong>{f.nome}</strong>
                            <small>{[f.cnpj, f.telefone && formatPhone(f.telefone), f.email].filter(Boolean).join(" · ") || "Sem contato cadastrado"}</small>
                        </div>
                        <button type="button" className="est-btn-icone perigo" onClick={() => inativar(f)} title="Inativar fornecedor" aria-label={`Inativar ${f.nome}`}>
                            <Power size={15} strokeWidth={2} />
                        </button>
                    </div>
                ))}
            </div>
            <div className="est-form-grid">
                <div className="field inteiro">
                    <label>Nome *</label>
                    <input placeholder="Ex.: Dental Sul Distribuidora" value={form.nome} onChange={set("nome")} maxLength={120} />
                </div>
                <div className="field">
                    <label>CNPJ</label>
                    <input placeholder="00.000.000/0000-00" value={form.cnpj} onChange={set("cnpj")} maxLength={20} />
                </div>
                <div className="field">
                    <label>Telefone</label>
                    <input placeholder="(62) 99999-0000" value={form.telefone} onChange={set("telefone")} maxLength={20} />
                </div>
                <div className="field inteiro">
                    <label>E-mail</label>
                    <input type="email" placeholder="contato@fornecedor.com" value={form.email} onChange={set("email")} maxLength={120} />
                </div>
            </div>
        </ModalEstoque>
    );
}

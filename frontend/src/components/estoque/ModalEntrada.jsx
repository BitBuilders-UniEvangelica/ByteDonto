import { useState } from "react";
import { useAuth } from "../../context/AuthContext";
import { apiRegistrarEntradaEstoque } from "../../services/api";
import { formatCurrency } from "../../utils/formatters";
import ModalEstoque from "./ModalEstoque";
import CampoFornecedor from "./CampoFornecedor";
import { resolverFornecedor } from "./fornecedorUtils";
import { hojeISO } from "./estoqueUtils";

/* Registrar entrada (compra ou reposição). itemFixo: abre já com o item escolhido. */
export default function ModalEntrada({ itens, itemFixo, fornecedores, onFornecedorCriado, onFechar, onSalvo }) {
    const { token } = useAuth();
    const [form, setForm] = useState({
        item_id: itemFixo?.id || "",
        quantidade: "",
        lote: "",
        validade: "",
        fornecedor_id: itemFixo?.fornecedor_id || "",
        nota_fiscal: "",
        valor_unitario: "",
        data: hojeISO(),
    });
    const [novoFornecedor, setNovoFornecedor] = useState("");
    const [erro, setErro] = useState("");
    const [salvando, setSalvando] = useState(false);

    const set = (campo) => (e) => setForm(f => ({ ...f, [campo]: e.target.value }));
    const total = Number(form.quantidade || 0) * Number(form.valor_unitario || 0);

    function escolherItem(e) {
        const id = e.target.value;
        const item = itens.find(i => i.id === id);
        // Sugere o fornecedor principal do item, se ainda não escolheram outro
        setForm(f => ({ ...f, item_id: id, fornecedor_id: f.fornecedor_id || item?.fornecedor_id || "" }));
    }

    async function salvar() {
        if (!form.item_id) return setErro("Selecione o item.");
        if (!(Number(form.quantidade) > 0)) return setErro("Informe uma quantidade maior que zero.");
        if (!form.lote.trim()) return setErro("Informe o lote.");
        if (!form.validade) return setErro("Informe a validade.");
        if (!form.fornecedor_id) return setErro("Selecione o fornecedor.");
        if (!form.data) return setErro("Informe a data da entrada.");
        if (form.data > hojeISO()) return setErro("A data da entrada não pode ser no futuro.");

        setSalvando(true);
        setErro("");
        try {
            const fornecedor_id = await resolverFornecedor(token, form.fornecedor_id, novoFornecedor, onFornecedorCriado);
            await apiRegistrarEntradaEstoque(token, {
                ...form,
                lote: form.lote.trim(),
                fornecedor_id,
                quantidade: Number(form.quantidade),
                valor_unitario: form.valor_unitario === "" ? null : Number(form.valor_unitario),
            });
            onSalvo();
        } catch (e) {
            setErro(e.message);
        } finally {
            setSalvando(false);
        }
    }

    return (
        <ModalEstoque
            titulo="Registrar Entrada"
            subtitulo="Compra ou reposição de estoque."
            erro={erro}
            salvando={salvando}
            onCancelar={onFechar}
            onSalvar={salvar}
            textoSalvar="Registrar entrada"
        >
            <div className="est-form-grid">
                <div className="field inteiro">
                    <label>Item *</label>
                    <select value={form.item_id} onChange={escolherItem} disabled={Boolean(itemFixo)}>
                        <option value="">Selecione o item...</option>
                        {itens.map(i => <option key={i.id} value={i.id}>{i.nome}</option>)}
                    </select>
                </div>
            </div>
            <div className="est-form-grid tres" style={{ marginTop: "0.9rem" }}>
                <div className="field">
                    <label>Quantidade *</label>
                    <input type="number" min="0" step="any" placeholder="0" value={form.quantidade} onChange={set("quantidade")} />
                </div>
                <div className="field">
                    <label>Lote *</label>
                    <input placeholder="Ex.: LD26931" value={form.lote} onChange={set("lote")} maxLength={60} />
                </div>
                <div className="field">
                    <label>Validade *</label>
                    <input type="date" value={form.validade} onChange={set("validade")} />
                </div>
            </div>
            <div className="est-form-grid" style={{ marginTop: "0.9rem" }}>
                <CampoFornecedor
                    rotulo="Fornecedor"
                    obrigatorio
                    fornecedores={fornecedores}
                    valor={form.fornecedor_id}
                    onChange={v => setForm(f => ({ ...f, fornecedor_id: v }))}
                    novoNome={novoFornecedor}
                    onNovoNome={setNovoFornecedor}
                />
                <div className="field">
                    <label>Nota fiscal</label>
                    <input placeholder="Ex.: 004692" value={form.nota_fiscal} onChange={set("nota_fiscal")} maxLength={60} />
                </div>
                <div className="field">
                    <label>Valor unitário (R$)</label>
                    <input type="number" min="0" step="0.01" placeholder="0,00" value={form.valor_unitario} onChange={set("valor_unitario")} />
                </div>
                <div className="field">
                    <label>Data da entrada *</label>
                    <input type="date" max={hojeISO()} value={form.data} onChange={set("data")} />
                </div>
            </div>
            <div className="est-total">
                <span>Total da entrada</span>
                <strong>{formatCurrency(total)}</strong>
            </div>
        </ModalEstoque>
    );
}

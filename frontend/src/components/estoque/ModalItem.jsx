import { useState } from "react";
import { useAuth } from "../../context/AuthContext";
import { apiCriarItemEstoque, apiAtualizarItemEstoque } from "../../services/api";
import ModalEstoque from "./ModalEstoque";
import CampoFornecedor from "./CampoFornecedor";
import { resolverFornecedor } from "./fornecedorUtils";
import { CATEGORIAS, UNIDADES } from "./estoqueUtils";

/* Adicionar item (com estoque inicial opcional) ou editar o cadastro de um item.
   Na edição o saldo não aparece: ele só muda por entrada ou saída. */
export default function ModalItem({ item, fornecedores, onFornecedorCriado, onFechar, onSalvo }) {
    const { token } = useAuth();
    const editando = Boolean(item);
    const [form, setForm] = useState(() => ({
        nome: item?.nome || "",
        categoria: item?.categoria || "",
        unidade: item?.unidade || "",
        estoque_minimo: item ? String(Number(item.estoque_minimo)) : "",
        quantidade_inicial: "",
        lote: "",
        validade: "",
        fornecedor_id: item?.fornecedor_id || "",
        localizacao: item?.localizacao || "",
        observacoes: item?.observacoes || "",
    }));
    const [novoFornecedor, setNovoFornecedor] = useState("");
    const [erro, setErro] = useState("");
    const [salvando, setSalvando] = useState(false);

    const set = (campo) => (e) => setForm(f => ({ ...f, [campo]: e.target.value }));

    async function salvar() {
        if (!form.nome.trim()) return setErro("Informe o nome do item.");
        if (!form.categoria) return setErro("Selecione a categoria.");
        if (!form.unidade) return setErro("Selecione a unidade.");
        if (form.estoque_minimo === "" || Number(form.estoque_minimo) < 0) return setErro("Informe um estoque mínimo válido.");
        if (form.quantidade_inicial !== "" && Number(form.quantidade_inicial) < 0) return setErro("A quantidade inicial não pode ser negativa.");

        setSalvando(true);
        setErro("");
        try {
            const fornecedor_id = await resolverFornecedor(token, form.fornecedor_id, novoFornecedor, onFornecedorCriado);
            const dados = {
                nome: form.nome.trim(),
                categoria: form.categoria,
                unidade: form.unidade,
                estoque_minimo: Number(form.estoque_minimo),
                fornecedor_id,
                localizacao: form.localizacao,
                observacoes: form.observacoes,
            };
            if (!editando) {
                dados.quantidade_inicial = Number(form.quantidade_inicial || 0);
                dados.lote = form.lote;
                dados.validade = form.validade || null;
            }
            const salvo = editando
                ? await apiAtualizarItemEstoque(token, item.id, dados)
                : await apiCriarItemEstoque(token, dados);
            onSalvo(salvo);
        } catch (e) {
            setErro(e.message);
        } finally {
            setSalvando(false);
        }
    }

    return (
        <ModalEstoque
            titulo={editando ? "Editar Item" : "Adicionar Item"}
            subtitulo={editando ? "Altere o cadastro do material ou insumo." : "Novo material ou insumo do estoque."}
            erro={erro}
            salvando={salvando}
            onCancelar={onFechar}
            onSalvar={salvar}
            textoSalvar={editando ? "Salvar alterações" : "Salvar item"}
        >
            <div className="est-form-grid">
                <div className="field inteiro">
                    <label>Nome do item *</label>
                    <input placeholder="Ex.: Resina Composta A2" value={form.nome} onChange={set("nome")} maxLength={120} />
                </div>
                <div className="field">
                    <label>Categoria *</label>
                    <select value={form.categoria} onChange={set("categoria")}>
                        <option value="">Selecione...</option>
                        {CATEGORIAS.map(c => <option key={c} value={c}>{c}</option>)}
                    </select>
                </div>
                <div className="field">
                    <label>Unidade *</label>
                    <select value={form.unidade} onChange={set("unidade")}>
                        <option value="">Selecione...</option>
                        {UNIDADES.map(u => <option key={u} value={u}>{u}</option>)}
                    </select>
                </div>
                <div className="field">
                    <label>Estoque mínimo *</label>
                    <input type="number" min="0" step="any" placeholder="0" value={form.estoque_minimo} onChange={set("estoque_minimo")} />
                </div>
                {!editando && (
                    <>
                        <div className="field">
                            <label>Quantidade inicial</label>
                            <input type="number" min="0" step="any" placeholder="0" value={form.quantidade_inicial} onChange={set("quantidade_inicial")} />
                        </div>
                        <div className="field">
                            <label>Lote</label>
                            <input placeholder="Ex.: R25A118" value={form.lote} onChange={set("lote")} maxLength={60} />
                        </div>
                        <div className="field">
                            <label>Validade</label>
                            <input type="date" value={form.validade} onChange={set("validade")} />
                        </div>
                    </>
                )}
                <CampoFornecedor
                    rotulo="Fornecedor"
                    fornecedores={fornecedores}
                    valor={form.fornecedor_id}
                    onChange={v => setForm(f => ({ ...f, fornecedor_id: v }))}
                    novoNome={novoFornecedor}
                    onNovoNome={setNovoFornecedor}
                />
                <div className="field">
                    <label>Localização</label>
                    <input placeholder="Ex.: Armário 2 - Gaveta B" value={form.localizacao} onChange={set("localizacao")} maxLength={120} />
                </div>
                <div className="field inteiro">
                    <label>Observações</label>
                    <textarea placeholder="Informações adicionais sobre o item..." value={form.observacoes} onChange={set("observacoes")} maxLength={1000} />
                </div>
            </div>
        </ModalEstoque>
    );
}

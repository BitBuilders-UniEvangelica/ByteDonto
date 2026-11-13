import { NOVO_FORNECEDOR } from "./fornecedorUtils";

/* Select de fornecedor com a opção "+ Cadastrar novo fornecedor", que troca o
   select por um campo de nome. O cadastro acontece ao salvar o modal
   (ver resolverFornecedor em fornecedorUtils.js), para o usuário não precisar sair do formulário. */
export default function CampoFornecedor({ rotulo, obrigatorio, fornecedores, valor, onChange, novoNome, onNovoNome }) {
    const criando = valor === NOVO_FORNECEDOR;
    return (
        <div className="field">
            <label>{rotulo}{obrigatorio ? " *" : ""}</label>
            {criando ? (
                <div style={{ display: "flex", gap: "0.5rem" }}>
                    <input
                        autoFocus
                        placeholder="Nome do novo fornecedor"
                        value={novoNome}
                        onChange={e => onNovoNome(e.target.value)}
                    />
                    <button type="button" className="est-btn" onClick={() => { onChange(""); onNovoNome(""); }}>Voltar</button>
                </div>
            ) : (
                <select value={valor} onChange={e => onChange(e.target.value)}>
                    <option value="">{obrigatorio ? "Selecione o fornecedor..." : "Selecione (opcional)..."}</option>
                    {fornecedores.map(f => <option key={f.id} value={f.id}>{f.nome}</option>)}
                    <option value={NOVO_FORNECEDOR}>+ Cadastrar novo fornecedor</option>
                </select>
            )}
        </div>
    );
}

import { apiCriarFornecedor } from "../../services/api";

export const NOVO_FORNECEDOR = "__novo";

/* Devolve o id do fornecedor escolhido, cadastrando antes se for um novo.
   onCriado recebe o fornecedor criado (para atualizar a lista da tela). */
export async function resolverFornecedor(token, valor, novoNome, onCriado) {
    if (valor !== NOVO_FORNECEDOR) return valor || null;
    const nome = novoNome.trim();
    if (!nome) throw new Error("Informe o nome do novo fornecedor.");
    const criado = await apiCriarFornecedor(token, { nome });
    onCriado?.(criado);
    return criado.id;
}

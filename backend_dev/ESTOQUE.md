# Módulo de estoque — contrato da API

Controle de materiais e insumos da clínica, com saldo por lote (validade e
rastreabilidade) e histórico de todas as entradas e saídas.

Prefixo: `/api/estoque` · Header: `Authorization: Bearer <token>`
Permissão: chave `estoque` (Dono sempre; Especialista e Recepção por padrão,
o Dono pode revogar em Equipe › Permissões).

## Regras

| Regra | Comportamento |
|---|---|
| Saldo | Saldo do item = soma dos lotes. Só muda por entrada ou saída; editar o item não mexe no saldo. |
| Status do item | `Esgotado` (saldo 0), `Estoque baixo` (saldo ≤ mínimo) ou `Normal`. |
| Entrada | Soma no lote com o mesmo código e validade; senão cria um lote novo. |
| Saída | Sai de um lote específico e não pode passar do saldo dele (409). |
| Datas | Data da entrada/saída não pode ser no futuro. |
| Exclusão | Não existe. Item e fornecedor são inativados (`ativo: false`); lotes e movimentações ficam preservados. |

## Rotas

### Itens
- `GET /itens`: ativos, com `quantidade_atual`, `status`, `proximo_vencimento` e `fornecedor.nome`. `?todos=1` inclui inativos.
- `POST /itens` → 201. `{ nome*, categoria* (Material|Insumo), unidade*, estoque_minimo*, quantidade_inicial?, lote?, validade?, fornecedor_id?, localizacao?, observacoes? }`. Com `quantidade_inicial > 0`, cria o primeiro lote e a movimentação "Estoque inicial".
- `GET /itens/<id>`: item + `lotes` (só com saldo) + `movimentacoes` (últimas 10).
- `PUT /itens/<id>`: os mesmos campos de cadastro (parcial).
- `DELETE /itens/<id>`: inativa.

Unidades aceitas: `un, cx, pct, par, ml, l, g, kg, frasco, ampola, tubo, seringa, rolo`.

### Movimentações
- `POST /entradas` → 201. `{ item_id*, quantidade*, lote*, validade*, fornecedor_id*, data*, nota_fiscal?, valor_unitario? }`
- `POST /saidas` → 201. `{ item_id*, lote_id*, quantidade*, motivo*, data*, responsavel_id*, paciente_id?, procedimento?, observacao? }`.
  Motivos: `Uso em procedimento`, `Vencimento`, `Perda / avaria`, `Ajuste de inventário`, `Doação / transferência`.
- `GET /movimentacoes`: filtros `?item_id=`, `?tipo=Entrada|Saída`, `?limit=` (padrão 200, máx. 1000).
- `GET /resumo?dias=30`: `{ movimentacoes_mes, mais_consumidos: [{ item_id, nome, unidade, quantidade }] }` (top 5 em saídas no período).

### Fornecedores
- `GET /fornecedores` (`?todos=1` inclui inativos) · `POST /fornecedores` `{ nome*, cnpj?, telefone?, email? }` · `PUT /fornecedores/<id>` (aceita `ativo`).

## Banco

Tabelas `fornecedores_estoque`, `itens_estoque`, `lotes_estoque` e
`movimentacoes_estoque` em `database_local.sql`. Para criar no banco local:
`venv/bin/python init_db.py` (idempotente, não apaga dados).

Testes: `tests/test_estoque.py` (14 testes).

## Pendências

- Produção (`backend/` + Supabase): as tabelas e as rotas ainda não existem lá.
- O saldo do lote é atualizado com leitura + escrita, sem transação. O `CHECK (quantidade >= 0)`
  impede saldo negativo, mas duas saídas simultâneas do mesmo lote podem disputar o saldo.
  Em produção, mover a baixa para uma função SQL (RPC) atômica.

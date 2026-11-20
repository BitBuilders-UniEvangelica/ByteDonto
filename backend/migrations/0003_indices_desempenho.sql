-- ============================================================
-- 0003 — Índices para as listagens paginadas
-- ============================================================
-- Migration ADITIVA e IDEMPOTENTE: só cria índices (IF NOT EXISTS).
-- Não altera tabelas, dados, RLS nem funções.
--
-- Cada índice cobre o filtro + a ordenação de uma listagem, para o banco
-- entregar a página pedida (LIMIT/OFFSET) sem ordenar a tabela inteira:
--   * pacientes:    lista da clínica, mais recentes primeiro; ordem por nome
--                   no campo de seleção (/api/pacientes/opcoes).
--   * atendimentos: agenda do período (clinica_id + data_agendada) e
--                   histórico/última consulta de cada paciente.
--   * faturamento:  lançamentos da clínica, mais recentes primeiro.
-- ============================================================

CREATE INDEX IF NOT EXISTS pacientes_clinica_criacao_idx
    ON pacientes (clinica_id, created_at DESC, id);

CREATE INDEX IF NOT EXISTS pacientes_clinica_nome_idx
    ON pacientes (clinica_id, nome);

CREATE INDEX IF NOT EXISTS atendimentos_clinica_data_idx
    ON atendimentos (clinica_id, data_agendada);

CREATE INDEX IF NOT EXISTS atendimentos_paciente_data_idx
    ON atendimentos (paciente_id, data_agendada DESC);

CREATE INDEX IF NOT EXISTS faturamento_clinica_criacao_idx
    ON faturamento (clinica_id, created_at DESC, id);

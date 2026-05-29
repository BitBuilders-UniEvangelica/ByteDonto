-- ============================================================
-- BYTEDONTO — LIMPEZA DO BANCO (Supabase)
-- ============================================================
-- O banco atual mistura tabelas do projeto ANTIGO (perfil pessoal)
-- com as do projeto NOVO (ByteDonto / repositório BitBuilders).
-- Este script ajuda a identificar e remover com segurança as tabelas
-- obsoletas, mantendo APENAS as 9 que o sistema atual usa.
--
-- Tabelas usadas pelo projeto atual (NÃO REMOVER):
--   clinicas, usuarios, pacientes, atendimentos, faturamento,
--   planos_tratamento, plano_itens, paciente_imagens, auditoria_prontuario
--
-- COMO USAR (faça na ordem):
--   1. Rode o PASSO 1 e leia o resultado: ele marca cada tabela do
--      schema public como "MANTER" ou "OBSOLETA (candidata a remover)".
--   2. Confira a lista de OBSOLETAS. Tenha CERTEZA de que nenhuma
--      guarda dado que você ainda quer. Faça um backup antes (Supabase
--      -> Database -> Backups, ou pg_dump) — DROP é irreversível.
--   3. Rode o PASSO 2 para gerar os comandos DROP automaticamente,
--      OU use o PASSO 3 (manual) descomentando linha a linha.
-- ============================================================


-- ------------------------------------------------------------
-- PASSO 1 — DIAGNÓSTICO: o que existe e o que é obsoleto
-- ------------------------------------------------------------
SELECT
    table_name,
    CASE
        WHEN table_name IN (
            'clinicas', 'usuarios', 'pacientes', 'atendimentos',
            'faturamento', 'planos_tratamento', 'plano_itens',
            'paciente_imagens', 'auditoria_prontuario'
        ) THEN 'MANTER'
        ELSE 'OBSOLETA (candidata a remover)'
    END AS situacao
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_type = 'BASE TABLE'
ORDER BY situacao DESC, table_name;


-- ------------------------------------------------------------
-- PASSO 2 — GERAR os comandos DROP das tabelas obsoletas
-- ------------------------------------------------------------
-- Isto NÃO apaga nada: apenas IMPRIME os comandos prontos.
-- Copie a saída, revise com cuidado e cole numa nova query para executar.
-- (CASCADE remove também views/constraints que dependem da tabela.)
SELECT string_agg(
    format('DROP TABLE IF EXISTS public.%I CASCADE;', table_name),
    E'\n'
) AS comandos_para_revisar_e_executar
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_type = 'BASE TABLE'
  AND table_name NOT IN (
      'clinicas', 'usuarios', 'pacientes', 'atendimentos',
      'faturamento', 'planos_tratamento', 'plano_itens',
      'paciente_imagens', 'auditoria_prontuario'
  );


-- ------------------------------------------------------------
-- PASSO 3 — (ALTERNATIVA MANUAL) Remoção tabela a tabela
-- ------------------------------------------------------------
-- Se preferir controlar manualmente, descomente e ajuste os nomes
-- conforme a lista de OBSOLETAS que o PASSO 1 retornou. Exemplo:
--
-- DROP TABLE IF EXISTS public.nome_da_tabela_antiga CASCADE;
-- DROP TABLE IF EXISTS public.outra_tabela_antiga CASCADE;
--
-- NUNCA remova tabelas dos schemas `auth`, `storage` ou `realtime`
-- (são gerenciadas pelo Supabase). Mexa apenas no schema `public`.

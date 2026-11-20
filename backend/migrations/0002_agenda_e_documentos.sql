-- ============================================================
-- 0002 — Consistência da agenda e proteção dos documentos clínicos
-- ============================================================
-- Migration ADITIVA e IDEMPOTENTE (CREATE OR REPLACE / IF NOT EXISTS /
-- DROP ... IF EXISTS + CREATE). Não apaga nem altera dados existentes.
-- APLIQUE PRIMEIRO EM HOMOLOGAÇÃO.
--
-- 1. Agenda (tabela atendimentos):
--    * um profissional não tem dois atendimentos simultâneos na mesma clínica;
--    * intervalos semiabertos [início, início + duração): 09:00–09:30 e
--      09:30–10:00 NÃO conflitam;
--    * atendimento Cancelado não ocupa horário;
--    * fluxo de status documentado: Agendado → Aguardando → Finalizado/Cancelado/Faltou
--      (Agendado também pode ir direto a Cancelado/Faltou/Finalizado, como a
--      agenda e o painel do especialista já fazem). Finalizado, Cancelado e
--      Faltou são finais;
--    * atendimento encerrado não é remarcado (data/duração/profissional);
--    * paciente e clínica de um atendimento não mudam;
--    * o mesmo paciente não recebe dois agendamentos idênticos (mesmo início),
--      o que barra duplo clique / requisição repetida.
--
--    Por que trigger + advisory lock e não EXCLUDE USING gist:
--    - a constraint de exclusão falharia ao ser criada se a produção já tiver
--      sobreposições antigas (a API nunca validou isso) e não aceita NOT VALID;
--    - exigiria a extensão btree_gist;
--    O trigger valida toda gravação NOVA, serializando as gravações de agenda
--    da mesma clínica com pg_advisory_xact_lock (liberado no fim da transação).
--    A consulta de conflito roda depois de obter o lock e, por estar numa função
--    VOLATILE em READ COMMITTED, enxerga o que a transação concorrente acabou de
--    gravar — duas requisições simultâneas nunca reservam o mesmo horário.
--    Vale para os dois modos (PostgREST e PostgreSQL local), pois roda no banco.
--
-- Convenção de horário: data_agendada guarda o HORÁRIO DE PAREDE da clínica
-- (o que o frontend envia, sem fuso). Comparações usam a mesma convenção.
-- ============================================================

CREATE OR REPLACE FUNCTION public.atendimentos_validar()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = public, pg_temp
AS $$
DECLARE
    v_fim TIMESTAMPTZ;
    v_conflito RECORD;
    v_bloqueia BOOLEAN := COALESCE(NEW.status, 'Agendado') <> 'Cancelado';
    v_mudou_agenda BOOLEAN := FALSE;
    v_verificar BOOLEAN := FALSE;
    v_finais CONSTANT TEXT[] := ARRAY['Finalizado', 'Cancelado', 'Faltou'];
BEGIN
    -- Duração: só valida quando é gravada/alterada (dados antigos não travam
    -- edições de outros campos, como a evolução clínica).
    IF NEW.duracao_minutos IS NOT NULL AND (NEW.duracao_minutos < 5 OR NEW.duracao_minutos > 480) THEN
        IF TG_OP = 'INSERT' THEN
            RAISE EXCEPTION 'DURACAO_INVALIDA' USING ERRCODE = 'check_violation';
        ELSIF NEW.duracao_minutos IS DISTINCT FROM OLD.duracao_minutos THEN
            RAISE EXCEPTION 'DURACAO_INVALIDA' USING ERRCODE = 'check_violation';
        END IF;
    END IF;

    IF TG_OP = 'UPDATE' THEN
        IF NEW.clinica_id IS DISTINCT FROM OLD.clinica_id THEN
            RAISE EXCEPTION 'ATENDIMENTO_IMUTAVEL|clinica';
        END IF;
        IF NEW.paciente_id IS DISTINCT FROM OLD.paciente_id THEN
            RAISE EXCEPTION 'ATENDIMENTO_IMUTAVEL|paciente';
        END IF;

        v_mudou_agenda := NEW.data_agendada IS DISTINCT FROM OLD.data_agendada
            OR COALESCE(NEW.duracao_minutos, 30) IS DISTINCT FROM COALESCE(OLD.duracao_minutos, 30)
            OR NEW.dentista_id IS DISTINCT FROM OLD.dentista_id;

        IF COALESCE(OLD.status, 'Agendado') = ANY (v_finais) AND v_mudou_agenda THEN
            RAISE EXCEPTION 'ATENDIMENTO_ENCERRADO|%', OLD.status;
        END IF;

        IF NEW.status IS DISTINCT FROM OLD.status AND NOT (
               (COALESCE(OLD.status, 'Agendado') = 'Agendado'
                    AND NEW.status IN ('Aguardando', 'Faltou', 'Cancelado', 'Finalizado'))
            OR (OLD.status = 'Aguardando'
                    AND NEW.status IN ('Finalizado', 'Cancelado', 'Faltou'))
        ) THEN
            RAISE EXCEPTION 'TRANSICAO_INVALIDA|%|%', OLD.status, NEW.status;
        END IF;

        v_verificar := v_bloqueia AND NEW.dentista_id IS NOT NULL AND v_mudou_agenda;
    ELSE
        v_verificar := v_bloqueia AND NEW.dentista_id IS NOT NULL;
    END IF;

    IF NOT v_verificar AND NOT (TG_OP = 'INSERT' AND v_bloqueia) THEN
        RETURN NEW;
    END IF;

    -- Serializa as gravações de agenda da clínica (até o fim da transação).
    PERFORM pg_advisory_xact_lock(hashtextextended('bytedonto:agenda:' || NEW.clinica_id::text, 0));

    IF v_verificar THEN
        v_fim := NEW.data_agendada + make_interval(mins => COALESCE(NEW.duracao_minutos, 30));
        SELECT a.data_agendada AS inicio,
               a.data_agendada + make_interval(mins => COALESCE(a.duracao_minutos, 30)) AS fim
          INTO v_conflito
          FROM atendimentos a
         WHERE a.clinica_id = NEW.clinica_id
           AND a.dentista_id = NEW.dentista_id
           AND a.id IS DISTINCT FROM NEW.id
           AND COALESCE(a.status, 'Agendado') <> 'Cancelado'
           AND a.data_agendada < v_fim
           AND a.data_agendada + make_interval(mins => COALESCE(a.duracao_minutos, 30)) > NEW.data_agendada
         ORDER BY a.data_agendada
         LIMIT 1;
        IF FOUND THEN
            RAISE EXCEPTION 'CONFLITO_HORARIO|%|%',
                to_char(v_conflito.inicio AT TIME ZONE 'UTC', 'DD/MM/YYYY HH24:MI'),
                to_char(v_conflito.fim AT TIME ZONE 'UTC', 'HH24:MI')
                USING ERRCODE = 'exclusion_violation';
        END IF;
    END IF;

    IF TG_OP = 'INSERT' AND v_bloqueia AND EXISTS (
        SELECT 1 FROM atendimentos a
         WHERE a.clinica_id = NEW.clinica_id
           AND a.paciente_id = NEW.paciente_id
           AND a.data_agendada = NEW.data_agendada
           AND COALESCE(a.status, 'Agendado') <> 'Cancelado'
    ) THEN
        RAISE EXCEPTION 'AGENDAMENTO_DUPLICADO' USING ERRCODE = 'unique_violation';
    END IF;

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS atendimentos_validar ON atendimentos;
CREATE TRIGGER atendimentos_validar BEFORE INSERT OR UPDATE ON atendimentos
    FOR EACH ROW EXECUTE FUNCTION atendimentos_validar();

REVOKE ALL ON FUNCTION public.atendimentos_validar() FROM PUBLIC;
DO $$
DECLARE
    papel TEXT;
BEGIN
    FOREACH papel IN ARRAY ARRAY['anon', 'authenticated'] LOOP
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = papel) THEN
            EXECUTE format('REVOKE ALL ON FUNCTION public.atendimentos_validar() FROM %I', papel);
        END IF;
    END LOOP;
END;
$$;

-- Acelera a busca de conflito (profissional + período).
CREATE INDEX IF NOT EXISTS atendimentos_agenda_profissional_idx
    ON atendimentos(clinica_id, dentista_id, data_agendada);

-- ------------------------------------------------------------
-- 2. Documentos clínicos no Supabase Storage (só existe no Supabase)
--    * o bucket paciente-imagens é PRIVADO (sem URL pública permanente);
--    * policy RESTRICTIVE em storage.objects: anon/authenticated não leem,
--      listam, enviam nem apagam objetos deste bucket com a chave pública.
--      A API usa a service role e os links assinados (1 h) continuam valendo,
--      pois são validados pelo próprio Storage, sem passar pelo RLS do usuário.
--    Outros buckets não são afetados.
-- ------------------------------------------------------------
DO $$
BEGIN
    IF to_regclass('storage.buckets') IS NOT NULL THEN
        UPDATE storage.buckets SET public = FALSE WHERE id = 'paciente-imagens' AND public IS DISTINCT FROM FALSE;
    END IF;
    IF to_regclass('storage.objects') IS NOT NULL
       AND EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon')
       AND EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
        EXECUTE 'DROP POLICY IF EXISTS paciente_imagens_sem_acesso_direto ON storage.objects';
        EXECUTE $p$
            CREATE POLICY paciente_imagens_sem_acesso_direto ON storage.objects
                AS RESTRICTIVE FOR ALL TO anon, authenticated
                USING (bucket_id <> 'paciente-imagens')
                WITH CHECK (bucket_id <> 'paciente-imagens')
        $p$;
    END IF;
END;
$$;

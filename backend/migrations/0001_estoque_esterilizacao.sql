-- ============================================================
-- 0001 — Estoque e Esterilização (RF-020 · RNE-011 · RNE-018)
-- ============================================================
-- Migration ADITIVA e IDEMPOTENTE: só cria o que não existe
-- (IF NOT EXISTS / CREATE OR REPLACE / DROP POLICY IF EXISTS + CREATE).
-- Não apaga nem altera dados existentes. Pode rodar mais de uma vez.
--
-- Onde roda:
--   * Supabase (produção/homologação): SQL Editor ou psql com a conexão do projeto.
--     APLIQUE PRIMEIRO EM HOMOLOGAÇÃO.
--   * PostgreSQL local: aplicada automaticamente por init_db.py e pelos testes.
--
-- Modelo de acesso (igual às tabelas existentes):
--   * A API (Flask) é a ÚNICA porta de entrada. Ela usa a service role, que
--     ignora RLS, e aplica RBAC + isolamento por clínica (app/auth_utils.py).
--   * A anon key é pública (está no frontend, para o login com Google). Por
--     isso anon/authenticated NÃO têm privilégio nem policy nestas tabelas:
--     REVOKE ALL + RLS habilitado + policy RESTRICTIVE que nega tudo.
--   * Isolamento entre clínicas também no banco: triggers impedem que um
--     registro referencie item/lote/fornecedor/ciclo/equipamento/paciente de
--     OUTRA clínica — vale até para a service role.
-- ============================================================

-- ------------------------------------------------------------
-- 1. ESTERILIZAÇÃO
-- Sem exclusão física: equipamentos são inativados e ciclos/pacotes
-- ficam preservados como registro sanitário (RNE-018).
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS equipamentos_esterilizacao (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clinica_id UUID NOT NULL REFERENCES clinicas(id) ON DELETE CASCADE,
    identificacao TEXT NOT NULL,
    tipo TEXT NOT NULL DEFAULT 'Autoclave',
    fabricante TEXT,
    modelo TEXT,
    numero_serie TEXT,
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE (clinica_id, identificacao)
);

CREATE TABLE IF NOT EXISTS ciclos_esterilizacao (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clinica_id UUID NOT NULL REFERENCES clinicas(id) ON DELETE CASCADE,
    equipamento_id UUID NOT NULL REFERENCES equipamentos_esterilizacao(id),
    numero_ciclo INTEGER NOT NULL,
    iniciado_em TIMESTAMP WITH TIME ZONE NOT NULL,
    temperatura_c DECIMAL(5,1) NOT NULL,
    pressao_kgf_cm2 DECIMAL(4,2) NOT NULL,
    tempo_exposicao_min INTEGER NOT NULL,
    indicador_quimico TEXT NOT NULL DEFAULT 'Pendente'
        CHECK (indicador_quimico IN ('Aprovado', 'Reprovado', 'Pendente')),
    indicador_biologico TEXT NOT NULL DEFAULT 'Pendente'
        CHECK (indicador_biologico IN ('Aprovado', 'Reprovado', 'Pendente', 'Não realizado')),
    resultado TEXT NOT NULL DEFAULT 'Pendente'
        CHECK (resultado IN ('Aprovado', 'Reprovado', 'Pendente')),
    responsavel_id UUID REFERENCES usuarios(id),
    observacoes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE (equipamento_id, numero_ciclo)
);

CREATE TABLE IF NOT EXISTS pacotes_esterilizados (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clinica_id UUID NOT NULL REFERENCES clinicas(id) ON DELETE CASCADE,
    ciclo_id UUID NOT NULL REFERENCES ciclos_esterilizacao(id),
    codigo TEXT NOT NULL,
    conteudo TEXT NOT NULL,
    metodo TEXT NOT NULL DEFAULT 'Vapor saturado sob pressão',
    data_esterilizacao DATE NOT NULL,
    data_limite_uso DATE NOT NULL,
    responsavel_preparo_id UUID REFERENCES usuarios(id),
    estado TEXT NOT NULL DEFAULT 'Aguardando liberação'
        CHECK (estado IN ('Aguardando liberação', 'Disponível', 'Bloqueado', 'Utilizado')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE (clinica_id, codigo),
    CHECK (data_limite_uso >= data_esterilizacao)
);

CREATE INDEX IF NOT EXISTS ciclos_esterilizacao_clinica_idx
    ON ciclos_esterilizacao(clinica_id, iniciado_em DESC);
CREATE INDEX IF NOT EXISTS pacotes_esterilizados_ciclo_idx
    ON pacotes_esterilizados(ciclo_id);
CREATE INDEX IF NOT EXISTS pacotes_esterilizados_estado_idx
    ON pacotes_esterilizados(clinica_id, estado, data_limite_uso);

-- ------------------------------------------------------------
-- 2. ESTOQUE (materiais e insumos da clínica)
-- Saldo controlado por lote (validade/rastreabilidade). Cada entrada ou
-- saída gera uma movimentação (histórico/auditoria, nunca apagada).
-- Sem exclusão física: itens e fornecedores são inativados (ativo = false).
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fornecedores_estoque (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clinica_id UUID NOT NULL REFERENCES clinicas(id) ON DELETE CASCADE,
    nome TEXT NOT NULL,
    cnpj TEXT,
    telefone TEXT,
    email TEXT,
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE (clinica_id, nome)
);

CREATE TABLE IF NOT EXISTS itens_estoque (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clinica_id UUID NOT NULL REFERENCES clinicas(id) ON DELETE CASCADE,
    nome TEXT NOT NULL,
    categoria TEXT NOT NULL CHECK (categoria IN ('Material', 'Insumo')),
    unidade TEXT NOT NULL,
    estoque_minimo DECIMAL(12,2) NOT NULL DEFAULT 0 CHECK (estoque_minimo >= 0),
    fornecedor_id UUID REFERENCES fornecedores_estoque(id),
    localizacao TEXT,
    observacoes TEXT,
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS lotes_estoque (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clinica_id UUID NOT NULL REFERENCES clinicas(id) ON DELETE CASCADE,
    item_id UUID NOT NULL REFERENCES itens_estoque(id),
    lote TEXT,
    validade DATE,
    -- O CHECK é a última barreira contra saldo negativo.
    quantidade DECIMAL(12,2) NOT NULL DEFAULT 0 CHECK (quantidade >= 0),
    fornecedor_id UUID REFERENCES fornecedores_estoque(id),
    data_entrada DATE NOT NULL DEFAULT CURRENT_DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS movimentacoes_estoque (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clinica_id UUID NOT NULL REFERENCES clinicas(id) ON DELETE CASCADE,
    item_id UUID NOT NULL REFERENCES itens_estoque(id),
    lote_id UUID REFERENCES lotes_estoque(id),
    tipo TEXT NOT NULL CHECK (tipo IN ('Entrada', 'Saída')),
    quantidade DECIMAL(12,2) NOT NULL CHECK (quantidade > 0),
    data DATE NOT NULL,
    motivo TEXT,
    fornecedor_id UUID REFERENCES fornecedores_estoque(id),
    nota_fiscal TEXT,
    valor_unitario DECIMAL(12,2) CHECK (valor_unitario >= 0),
    paciente_id UUID REFERENCES pacientes(id),
    procedimento TEXT,
    responsavel_id UUID REFERENCES usuarios(id),
    observacao TEXT,
    registrado_por UUID REFERENCES usuarios(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS itens_estoque_clinica_idx ON itens_estoque(clinica_id, nome);
CREATE INDEX IF NOT EXISTS lotes_estoque_item_idx ON lotes_estoque(item_id, validade);
CREATE INDEX IF NOT EXISTS movimentacoes_estoque_item_idx ON movimentacoes_estoque(item_id, data DESC);
CREATE INDEX IF NOT EXISTS movimentacoes_estoque_clinica_idx ON movimentacoes_estoque(clinica_id, data DESC);

-- ------------------------------------------------------------
-- 3. ISOLAMENTO ENTRE CLÍNICAS NO BANCO
-- Trigger genérico: TG_ARGV = pares (coluna, tabela_referenciada). Se a
-- coluna estiver preenchida, o registro referenciado precisa ter o MESMO
-- clinica_id da linha gravada. Vale para qualquer papel, inclusive service role.
-- ------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.garantir_mesma_clinica()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = public, pg_temp
AS $$
DECLARE
    i INTEGER := 0;
    v_coluna TEXT;
    v_tabela TEXT;
    v_valor TEXT;
    v_ok BOOLEAN;
BEGIN
    WHILE i < TG_NARGS LOOP
        v_coluna := TG_ARGV[i];
        v_tabela := TG_ARGV[i + 1];
        v_valor := to_jsonb(NEW) ->> v_coluna;
        IF v_valor IS NOT NULL THEN
            EXECUTE format('SELECT EXISTS (SELECT 1 FROM %I WHERE id = $1::uuid AND clinica_id = $2)', v_tabela)
                INTO v_ok USING v_valor, NEW.clinica_id;
            IF NOT v_ok THEN
                RAISE EXCEPTION 'CLINICA_DIVERGENTE: %.% não pertence à clínica do registro', TG_TABLE_NAME, v_coluna
                    USING ERRCODE = 'foreign_key_violation';
            END IF;
        END IF;
        i := i + 2;
    END LOOP;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS itens_estoque_mesma_clinica ON itens_estoque;
CREATE TRIGGER itens_estoque_mesma_clinica BEFORE INSERT OR UPDATE ON itens_estoque
    FOR EACH ROW EXECUTE FUNCTION garantir_mesma_clinica('fornecedor_id', 'fornecedores_estoque');

DROP TRIGGER IF EXISTS lotes_estoque_mesma_clinica ON lotes_estoque;
CREATE TRIGGER lotes_estoque_mesma_clinica BEFORE INSERT OR UPDATE ON lotes_estoque
    FOR EACH ROW EXECUTE FUNCTION garantir_mesma_clinica(
        'item_id', 'itens_estoque', 'fornecedor_id', 'fornecedores_estoque');

DROP TRIGGER IF EXISTS movimentacoes_estoque_mesma_clinica ON movimentacoes_estoque;
CREATE TRIGGER movimentacoes_estoque_mesma_clinica BEFORE INSERT OR UPDATE ON movimentacoes_estoque
    FOR EACH ROW EXECUTE FUNCTION garantir_mesma_clinica(
        'item_id', 'itens_estoque', 'lote_id', 'lotes_estoque',
        'fornecedor_id', 'fornecedores_estoque', 'paciente_id', 'pacientes');

DROP TRIGGER IF EXISTS ciclos_esterilizacao_mesma_clinica ON ciclos_esterilizacao;
CREATE TRIGGER ciclos_esterilizacao_mesma_clinica BEFORE INSERT OR UPDATE ON ciclos_esterilizacao
    FOR EACH ROW EXECUTE FUNCTION garantir_mesma_clinica('equipamento_id', 'equipamentos_esterilizacao');

DROP TRIGGER IF EXISTS pacotes_esterilizados_mesma_clinica ON pacotes_esterilizados;
CREATE TRIGGER pacotes_esterilizados_mesma_clinica BEFORE INSERT OR UPDATE ON pacotes_esterilizados
    FOR EACH ROW EXECUTE FUNCTION garantir_mesma_clinica('ciclo_id', 'ciclos_esterilizacao');

-- ------------------------------------------------------------
-- 4. OPERAÇÕES ATÔMICAS DE ESTOQUE
-- Chamadas pela API via .rpc(). Cada função roda numa única transação:
-- o saldo nunca é "lido e depois gravado" pela aplicação, então operações
-- simultâneas não perdem atualização nem deixam saldo negativo.
-- SECURITY INVOKER: rodam com os privilégios de quem chama (a API).
-- ------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.estoque_registrar_entrada(
    p_clinica_id UUID,
    p_item_id UUID,
    p_quantidade NUMERIC,
    p_data DATE,
    p_lote TEXT,
    p_validade DATE,
    p_fornecedor_id UUID,
    p_registrado_por UUID,
    p_motivo TEXT DEFAULT 'Compra / reposição',
    p_nota_fiscal TEXT DEFAULT NULL,
    p_valor_unitario NUMERIC DEFAULT NULL
)
RETURNS TABLE (lote JSONB, movimentacao JSONB)
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = public, pg_temp
AS $$
DECLARE
    v_lote lotes_estoque%ROWTYPE;
    v_mov movimentacoes_estoque%ROWTYPE;
BEGIN
    IF p_quantidade IS NULL OR p_quantidade <= 0 THEN
        RAISE EXCEPTION 'QUANTIDADE_INVALIDA';
    END IF;

    -- Trava o item: entradas simultâneas do mesmo item ficam em fila, então
    -- não duplicam lote nem perdem soma. NO KEY UPDATE (e não UPDATE) para não
    -- conflitar com o KEY SHARE que as FKs das saídas pegam no item — com
    -- FOR UPDATE, entrada e saída simultâneas entravam em deadlock.
    PERFORM 1 FROM itens_estoque
     WHERE id = p_item_id AND clinica_id = p_clinica_id
       FOR NO KEY UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'ITEM_NAO_ENCONTRADO';
    END IF;

    -- Mesmo código de lote e mesma validade -> soma no lote existente.
    SELECT * INTO v_lote FROM lotes_estoque l
     WHERE l.clinica_id = p_clinica_id AND l.item_id = p_item_id
       AND l.lote IS NOT DISTINCT FROM p_lote
       AND l.validade IS NOT DISTINCT FROM p_validade
     ORDER BY l.created_at
     LIMIT 1
       FOR NO KEY UPDATE;

    IF FOUND THEN
        UPDATE lotes_estoque l SET quantidade = l.quantidade + p_quantidade
         WHERE l.id = v_lote.id
        RETURNING l.* INTO v_lote;
    ELSE
        INSERT INTO lotes_estoque (clinica_id, item_id, quantidade, data_entrada, lote, validade, fornecedor_id)
        VALUES (p_clinica_id, p_item_id, p_quantidade, p_data, p_lote, p_validade, p_fornecedor_id)
        RETURNING * INTO v_lote;
    END IF;

    INSERT INTO movimentacoes_estoque (
        clinica_id, item_id, lote_id, tipo, quantidade, data, motivo,
        responsavel_id, registrado_por, fornecedor_id, nota_fiscal, valor_unitario
    ) VALUES (
        p_clinica_id, p_item_id, v_lote.id, 'Entrada', p_quantidade, p_data, p_motivo,
        p_registrado_por, p_registrado_por, p_fornecedor_id, p_nota_fiscal, p_valor_unitario
    )
    RETURNING * INTO v_mov;

    RETURN QUERY SELECT to_jsonb(v_lote), to_jsonb(v_mov);
END;
$$;

CREATE OR REPLACE FUNCTION public.estoque_registrar_saida(
    p_clinica_id UUID,
    p_item_id UUID,
    p_lote_id UUID,
    p_quantidade NUMERIC,
    p_data DATE,
    p_motivo TEXT,
    p_responsavel_id UUID,
    p_registrado_por UUID,
    p_paciente_id UUID DEFAULT NULL,
    p_procedimento TEXT DEFAULT NULL,
    p_observacao TEXT DEFAULT NULL
)
RETURNS TABLE (lote JSONB, movimentacao JSONB)
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = public, pg_temp
AS $$
DECLARE
    v_lote lotes_estoque%ROWTYPE;
    v_mov movimentacoes_estoque%ROWTYPE;
    v_saldo NUMERIC;
BEGIN
    IF p_quantidade IS NULL OR p_quantidade <= 0 THEN
        RAISE EXCEPTION 'QUANTIDADE_INVALIDA';
    END IF;

    -- Baixa condicional e atômica: só debita se houver saldo suficiente.
    UPDATE lotes_estoque l SET quantidade = l.quantidade - p_quantidade
     WHERE l.id = p_lote_id AND l.clinica_id = p_clinica_id AND l.item_id = p_item_id
       AND l.quantidade >= p_quantidade
    RETURNING l.* INTO v_lote;

    IF NOT FOUND THEN
        SELECT l.quantidade INTO v_saldo FROM lotes_estoque l
         WHERE l.id = p_lote_id AND l.clinica_id = p_clinica_id AND l.item_id = p_item_id;
        IF NOT FOUND THEN
            RAISE EXCEPTION 'LOTE_NAO_ENCONTRADO';
        END IF;
        RAISE EXCEPTION 'SALDO_INSUFICIENTE:%', v_saldo;
    END IF;

    INSERT INTO movimentacoes_estoque (
        clinica_id, item_id, lote_id, tipo, quantidade, data, motivo,
        responsavel_id, registrado_por, paciente_id, procedimento, observacao
    ) VALUES (
        p_clinica_id, p_item_id, p_lote_id, 'Saída', p_quantidade, p_data, p_motivo,
        p_responsavel_id, p_registrado_por, p_paciente_id, p_procedimento, p_observacao
    )
    RETURNING * INTO v_mov;

    RETURN QUERY SELECT to_jsonb(v_lote), to_jsonb(v_mov);
END;
$$;

-- ------------------------------------------------------------
-- 5. RLS E PRIVILÉGIOS
-- ------------------------------------------------------------
DO $$
DECLARE
    t TEXT;
    tabelas TEXT[] := ARRAY[
        'equipamentos_esterilizacao', 'ciclos_esterilizacao', 'pacotes_esterilizados',
        'fornecedores_estoque', 'itens_estoque', 'lotes_estoque', 'movimentacoes_estoque'
    ];
BEGIN
    FOREACH t IN ARRAY tabelas LOOP
        EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', t);

        -- Nega qualquer acesso direto (PostgREST com anon/authenticated). Por ser
        -- RESTRICTIVE, nenhuma policy permissiva criada no futuro reabre o acesso
        -- sem remover esta explicitamente. A service role tem BYPASSRLS e o dono
        -- da tabela não é afetado (sem FORCE), então a API continua funcionando.
        EXECUTE format('DROP POLICY IF EXISTS sem_acesso_direto ON %I', t);
        EXECUTE format(
            'CREATE POLICY sem_acesso_direto ON %I AS RESTRICTIVE FOR ALL TO PUBLIC USING (false) WITH CHECK (false)', t);

        EXECUTE format('REVOKE ALL ON TABLE %I FROM PUBLIC', t);
        -- No Supabase, novas tabelas recebem GRANT ALL para anon/authenticated
        -- (default privileges). Removemos. Fora do Supabase os papéis não existem.
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
            EXECUTE format('REVOKE ALL ON TABLE %I FROM anon', t);
        END IF;
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
            EXECUTE format('REVOKE ALL ON TABLE %I FROM authenticated', t);
        END IF;
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN
            EXECUTE format('GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE %I TO service_role', t);
            -- Documenta quem acessa: só o servidor da API.
            EXECUTE format('DROP POLICY IF EXISTS api_servidor ON %I', t);
            EXECUTE format(
                'CREATE POLICY api_servidor ON %I FOR ALL TO service_role USING (true) WITH CHECK (true)', t);
        END IF;
    END LOOP;
END;
$$;

-- Funções: o PostgreSQL concede EXECUTE a PUBLIC por padrão e o Supabase as
-- expõe em /rest/v1/rpc. Só a API pode chamá-las.
REVOKE ALL ON FUNCTION public.estoque_registrar_entrada(UUID, UUID, NUMERIC, DATE, TEXT, DATE, UUID, UUID, TEXT, TEXT, NUMERIC) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.estoque_registrar_saida(UUID, UUID, UUID, NUMERIC, DATE, TEXT, UUID, UUID, UUID, TEXT, TEXT) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.garantir_mesma_clinica() FROM PUBLIC;

DO $$
DECLARE
    papel TEXT;
BEGIN
    FOREACH papel IN ARRAY ARRAY['anon', 'authenticated'] LOOP
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = papel) THEN
            EXECUTE format('REVOKE ALL ON FUNCTION public.estoque_registrar_entrada(UUID, UUID, NUMERIC, DATE, TEXT, DATE, UUID, UUID, TEXT, TEXT, NUMERIC) FROM %I', papel);
            EXECUTE format('REVOKE ALL ON FUNCTION public.estoque_registrar_saida(UUID, UUID, UUID, NUMERIC, DATE, TEXT, UUID, UUID, UUID, TEXT, TEXT) FROM %I', papel);
            EXECUTE format('REVOKE ALL ON FUNCTION public.garantir_mesma_clinica() FROM %I', papel);
        END IF;
    END LOOP;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN
        GRANT EXECUTE ON FUNCTION public.estoque_registrar_entrada(UUID, UUID, NUMERIC, DATE, TEXT, DATE, UUID, UUID, TEXT, TEXT, NUMERIC) TO service_role;
        GRANT EXECUTE ON FUNCTION public.estoque_registrar_saida(UUID, UUID, UUID, NUMERIC, DATE, TEXT, UUID, UUID, UUID, TEXT, TEXT) TO service_role;
    END IF;
END;
$$;

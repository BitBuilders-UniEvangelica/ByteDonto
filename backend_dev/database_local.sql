-- ============================================================
-- BYTEDONTO — BANCO LOCAL (PostgreSQL) PARA DESENVOLVIMENTO
-- ============================================================
-- Mesmo schema de produção (backend/database_completo.sql + migrações),
-- adaptado para rodar FORA do Supabase:
--   - O schema `auth` (que no Supabase é gerenciado por eles) é criado aqui,
--     com as tabelas mínimas que o backend_dev usa: auth.users e auth.sessions.
--   - UUIDs usam gen_random_uuid() (nativo do PostgreSQL 13+, sem extensão).
--   - Sem Row Level Security: no local não existe anon key nem acesso direto.
--
-- Normalmente você NÃO precisa rodar este arquivo na mão:
--     venv/bin/python init_db.py
-- Pode rodar mais de uma vez sem problema (tudo usa IF NOT EXISTS).
-- ============================================================

-- ------------------------------------------------------------
-- 0. AUTH (substitui o Supabase Auth)
-- ------------------------------------------------------------
CREATE SCHEMA IF NOT EXISTS auth;

CREATE TABLE IF NOT EXISTS auth.users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT NOT NULL UNIQUE,              -- sempre gravado em minúsculas
    encrypted_password TEXT NOT NULL,        -- hash (werkzeug/scrypt), nunca texto puro
    email_confirmed_at TIMESTAMP WITH TIME ZONE,
    last_sign_in_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Cada login cria uma sessão; o JWT carrega o id dela. Logout revoga a sessão.
CREATE TABLE IF NOT EXISTS auth.sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    revoked_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS auth_sessions_user_idx ON auth.sessions(user_id);

-- ------------------------------------------------------------
-- 1. CLÍNICAS (cada clínica é um "tenant")
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS clinicas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nome_fantasia TEXT NOT NULL,
    razao_social TEXT,
    cnpj TEXT UNIQUE,
    telefone TEXT,
    resumo TEXT,
    redes_sociais JSONB DEFAULT '{}'::jsonb,
    endereco JSONB DEFAULT '{}'::jsonb,
    dono_id UUID REFERENCES auth.users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ------------------------------------------------------------
-- 2. USUÁRIOS (perfis: Dono, Especialista, Recepção)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS usuarios (
    id UUID PRIMARY KEY REFERENCES auth.users(id),
    clinica_id UUID REFERENCES clinicas(id) ON DELETE CASCADE,
    nome TEXT NOT NULL,
    papel TEXT CHECK (papel IN ('Dono', 'Especialista', 'Recepção')) NOT NULL,
    permissoes JSONB DEFAULT '{}'::jsonb,
    ativo BOOLEAN DEFAULT TRUE,
    percentual_repasse NUMERIC(5,2) DEFAULT 0,
    cro TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ------------------------------------------------------------
-- 3. PACIENTES
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS pacientes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clinica_id UUID REFERENCES clinicas(id) ON DELETE CASCADE,
    nome TEXT NOT NULL,
    cpf TEXT,
    rg TEXT,
    data_nascimento DATE,
    genero TEXT,
    telefone_whatsapp TEXT,
    email TEXT,
    endereco JSONB DEFAULT '{}'::jsonb,
    anamnese JSONB DEFAULT '{}'::jsonb,
    odontograma JSONB DEFAULT '{}'::jsonb,
    status TEXT DEFAULT 'Ativo',
    updated_by UUID REFERENCES usuarios(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ------------------------------------------------------------
-- 4. ATENDIMENTOS / CONSULTAS
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS atendimentos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clinica_id UUID REFERENCES clinicas(id) ON DELETE CASCADE,
    paciente_id UUID REFERENCES pacientes(id) ON DELETE CASCADE,
    dentista_id UUID REFERENCES usuarios(id),
    data_agendada TIMESTAMP WITH TIME ZONE NOT NULL,
    duracao_minutos INTEGER DEFAULT 30,
    cadeira TEXT,
    queixa_principal TEXT,
    procedimentos_descritos TEXT,
    evolucao_clinica TEXT,
    tipo_atendimento TEXT,
    status TEXT DEFAULT 'Agendado'
        CONSTRAINT atendimentos_status_check
        CHECK (status IN ('Agendado', 'Aguardando', 'Cancelado', 'Finalizado', 'Faltou')),
    updated_by UUID REFERENCES usuarios(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ------------------------------------------------------------
-- 5. FATURAMENTO
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS faturamento (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clinica_id UUID REFERENCES clinicas(id) ON DELETE CASCADE,
    paciente_id UUID REFERENCES pacientes(id),
    atendimento_id UUID REFERENCES atendimentos(id),
    plano_item_id UUID,
    dentista_responsavel UUID REFERENCES usuarios(id),
    valor DECIMAL(10,2) NOT NULL,
    descricao TEXT,
    forma_pagamento TEXT,
    status_pagamento TEXT CHECK (status_pagamento IN ('Pago', 'Pendente', 'Cancelado')) DEFAULT 'Pendente',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ------------------------------------------------------------
-- 6. PLANOS DE TRATAMENTO
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS planos_tratamento (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clinica_id UUID REFERENCES clinicas(id) ON DELETE CASCADE,
    paciente_id UUID REFERENCES pacientes(id) ON DELETE CASCADE,
    dentista_id UUID REFERENCES usuarios(id),
    titulo TEXT NOT NULL DEFAULT 'Plano de Tratamento',
    status TEXT CHECK (status IN ('Orcamento', 'Aprovado', 'Em Andamento', 'Concluido', 'Cancelado')) DEFAULT 'Orcamento',
    valor_total DECIMAL(10,2) DEFAULT 0,
    observacoes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS plano_itens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plano_id UUID REFERENCES planos_tratamento(id) ON DELETE CASCADE,
    procedimento TEXT NOT NULL,
    dente TEXT,
    quantidade INTEGER DEFAULT 1,
    valor_unitario DECIMAL(10,2) DEFAULT 0,
    status TEXT CHECK (status IN ('Pendente', 'Concluido', 'Cancelado')) DEFAULT 'Pendente',
    ordem INTEGER DEFAULT 0
);

-- ------------------------------------------------------------
-- 7. IMAGENS / ARQUIVOS DO PACIENTE
-- (os arquivos em si ficam em backend_dev/storage/, não no banco)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS paciente_imagens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clinica_id UUID,
    paciente_id UUID REFERENCES pacientes(id) ON DELETE CASCADE,
    nome TEXT,
    storage_path TEXT NOT NULL,
    tipo TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ------------------------------------------------------------
-- 8. AUDITORIA DO PRONTUÁRIO (Res. CFO 226/2020)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS auditoria_prontuario (
    id BIGSERIAL PRIMARY KEY,
    clinica_id UUID,
    paciente_id UUID,
    usuario_id UUID REFERENCES usuarios(id),
    tabela TEXT NOT NULL,
    registro_id UUID NOT NULL,
    acao TEXT NOT NULL,
    campos JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS auditoria_prontuario_paciente_idx
    ON auditoria_prontuario(paciente_id, created_at DESC);
CREATE INDEX IF NOT EXISTS auditoria_prontuario_clinica_idx
    ON auditoria_prontuario(clinica_id, created_at DESC);

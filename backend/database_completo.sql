-- ============================================================
-- BYTEDONTO — SCRIPT COMPLETO DO BANCO DE DADOS
-- ============================================================
-- COMO USAR:
--   1. Abra o painel do Supabase do projeto
--   2. Menu lateral -> SQL Editor -> New query
--   3. Cole TODO este arquivo e clique em "Run"
-- Pode rodar mais de uma vez sem problema (tudo usa IF NOT EXISTS / DROP IF EXISTS).
-- Este script CRIA o banco do zero E também ATUALIZA bancos existentes.
-- ============================================================

-- Extensão necessária para uuid_generate_v4()
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ------------------------------------------------------------
-- 1. CLÍNICAS (cada clínica é um "tenant")
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS clinicas (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    nome_fantasia TEXT NOT NULL,
    razao_social TEXT,
    cnpj TEXT UNIQUE,
    telefone TEXT,
    endereco JSONB DEFAULT '{}'::jsonb,
    dono_id UUID REFERENCES auth.users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

ALTER TABLE clinicas ADD COLUMN IF NOT EXISTS telefone TEXT;
ALTER TABLE clinicas ADD COLUMN IF NOT EXISTS endereco JSONB DEFAULT '{}'::jsonb;

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
    percentual_repasse NUMERIC(5,2) DEFAULT 0,  -- % que o dentista recebe sobre os procedimentos que produziu
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS ativo BOOLEAN DEFAULT TRUE;
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS percentual_repasse NUMERIC(5,2) DEFAULT 0;

-- ------------------------------------------------------------
-- 3. PACIENTES
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS pacientes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
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

ALTER TABLE pacientes ADD COLUMN IF NOT EXISTS odontograma JSONB DEFAULT '{}'::jsonb;
ALTER TABLE pacientes ADD COLUMN IF NOT EXISTS updated_by UUID REFERENCES usuarios(id);
ALTER TABLE pacientes ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();

-- ------------------------------------------------------------
-- 4. ATENDIMENTOS / CONSULTAS
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS atendimentos (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    clinica_id UUID REFERENCES clinicas(id) ON DELETE CASCADE,
    paciente_id UUID REFERENCES pacientes(id) ON DELETE CASCADE,
    dentista_id UUID REFERENCES usuarios(id),
    data_agendada TIMESTAMP WITH TIME ZONE NOT NULL,
    duracao_minutos INTEGER DEFAULT 30,
    cadeira TEXT,
    procedimentos_descritos TEXT,
    evolucao_clinica TEXT,
    tipo_atendimento TEXT,
    status TEXT DEFAULT 'Agendado',
    updated_by UUID REFERENCES usuarios(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

ALTER TABLE atendimentos ADD COLUMN IF NOT EXISTS duracao_minutos INTEGER DEFAULT 30;
ALTER TABLE atendimentos ADD COLUMN IF NOT EXISTS cadeira TEXT;
ALTER TABLE atendimentos ADD COLUMN IF NOT EXISTS updated_by UUID REFERENCES usuarios(id);
ALTER TABLE atendimentos ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();

-- Status com 'Aguardando' (sala de espera após check-in)
ALTER TABLE atendimentos DROP CONSTRAINT IF EXISTS atendimentos_status_check;
ALTER TABLE atendimentos ADD CONSTRAINT atendimentos_status_check
  CHECK (status IN ('Agendado', 'Aguardando', 'Cancelado', 'Finalizado', 'Faltou'));

-- ------------------------------------------------------------
-- 5. FATURAMENTO
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS faturamento (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    clinica_id UUID REFERENCES clinicas(id) ON DELETE CASCADE,
    paciente_id UUID REFERENCES pacientes(id),
    atendimento_id UUID REFERENCES atendimentos(id),
    plano_item_id UUID,  -- vínculo opcional ao item do plano que gerou esta cobrança
    dentista_responsavel UUID REFERENCES usuarios(id),
    valor DECIMAL(10,2) NOT NULL,
    descricao TEXT,      -- procedimento descrito (ex: "Restauração dente 36"), aparece no extrato
    forma_pagamento TEXT,
    status_pagamento TEXT CHECK (status_pagamento IN ('Pago', 'Pendente', 'Cancelado')) DEFAULT 'Pendente',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

ALTER TABLE faturamento ADD COLUMN IF NOT EXISTS descricao TEXT;
ALTER TABLE faturamento ADD COLUMN IF NOT EXISTS plano_item_id UUID;

-- ------------------------------------------------------------
-- 6. PLANOS DE TRATAMENTO
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS planos_tratamento (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
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
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
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
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS paciente_imagens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    clinica_id UUID,
    paciente_id UUID REFERENCES pacientes(id) ON DELETE CASCADE,
    nome TEXT,
    storage_path TEXT NOT NULL,
    tipo TEXT,           -- "imagem" | "laudo" | "termo_consentimento" | "termo_lgpd"
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- A coluna 'url' antiga (pública) é removida — sempre geramos URL assinada agora
ALTER TABLE paciente_imagens DROP COLUMN IF EXISTS url;
ALTER TABLE paciente_imagens ADD COLUMN IF NOT EXISTS tipo TEXT;

-- ------------------------------------------------------------
-- 8. AUDITORIA DO PRONTUÁRIO (Res. CFO 226/2020)
-- Registra toda alteração relevante em pacientes / atendimentos / planos.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS auditoria_prontuario (
    id BIGSERIAL PRIMARY KEY,
    clinica_id UUID,
    paciente_id UUID,
    usuario_id UUID REFERENCES usuarios(id),
    tabela TEXT NOT NULL,                  -- 'pacientes' | 'atendimentos' | 'planos_tratamento'
    registro_id UUID NOT NULL,
    acao TEXT NOT NULL,                    -- 'INSERT' | 'UPDATE' | 'DELETE'
    campos JSONB DEFAULT '{}'::jsonb,      -- { campo: { antes, depois } }
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS auditoria_prontuario_paciente_idx
    ON auditoria_prontuario(paciente_id, created_at DESC);
CREATE INDEX IF NOT EXISTS auditoria_prontuario_clinica_idx
    ON auditoria_prontuario(clinica_id, created_at DESC);

-- ------------------------------------------------------------
-- 9. ROW LEVEL SECURITY
-- O backend acessa o banco com a service_role key (ignora RLS).
-- Manter RLS ligado protege contra acesso direto pela anon key.
-- ------------------------------------------------------------
ALTER TABLE clinicas             ENABLE ROW LEVEL SECURITY;
ALTER TABLE usuarios             ENABLE ROW LEVEL SECURITY;
ALTER TABLE pacientes            ENABLE ROW LEVEL SECURITY;
ALTER TABLE atendimentos         ENABLE ROW LEVEL SECURITY;
ALTER TABLE faturamento          ENABLE ROW LEVEL SECURITY;
ALTER TABLE planos_tratamento    ENABLE ROW LEVEL SECURITY;
ALTER TABLE plano_itens          ENABLE ROW LEVEL SECURITY;
ALTER TABLE paciente_imagens     ENABLE ROW LEVEL SECURITY;
ALTER TABLE auditoria_prontuario ENABLE ROW LEVEL SECURITY;

# Atualizações para o Documento de PI — versão 3.3

> Este arquivo descreve **o que precisa mudar** no Documento de Especificação de Projeto Integrador do ByteDonto (atualmente na v3.1) para refletir o estado real do sistema após a iteração de melhoria geral de 24/05/2026.
>
> Cada item indica a **página do PDF original** onde fica a mudança, e traz o texto **pronto pra copiar e colar** no Google Docs.

---

## 📑 Índice de mudanças

1. [Histórico de Versão — adicionar v3.3](#1-histórico-de-versão-página-4)
2. [Descrição do Produto — remover WhatsApp/IA](#2-descrição-do-produto-página-5)
3. [Resumo do Negócio — atualizar diferenciais](#3-resumo-do-negócio-página-5)
4. [Problemas Identificados — adicionar glosas e cobrança perdida](#4-problemas-identificados-página-5-6)
5. [Situação Atual do Projeto — REESCREVER](#5-situação-atual-do-projeto-página-7)
6. [Objetivos do Semestre — REESCREVER](#6-objetivos-do-semestre-página-7)
7. [Cronograma do Semestre — REESCREVER](#7-cronograma-do-semestre-páginas-7-8)
8. [Regras de Negócio — adicionar RNE-007, RNE-008, RNE-009](#8-regras-de-negócio-páginas-10-12)
9. [Requisitos Funcionais — atualizar status + adicionar RF-010 a RF-016](#9-requisitos-funcionais-páginas-12-13)
10. [Requisitos Não Funcionais — corrigir numeração + adicionar RNF-009, RNF-010](#10-requisitos-não-funcionais-páginas-13-14)
11. [Modelagem de Dados — 9 entidades reais (não 4)](#11-modelagem-de-dados-página-19)
12. [Estrutura e Manipulação — trocar SQLAlchemy por supabase-py](#12-estrutura-e-manipulação-página-20)
13. [Tecnologias — esclarecer hospedagem](#13-tecnologias-página-24)
14. [Frontend (22.1) — REESCREVER com telas reais](#14-frontend-221-página-25)
15. [Backend (22.2) — REESCREVER com 9 blueprints](#15-backend-222-página-25)
16. [Organização do Código (23) — sem models/utils fictícios](#16-organização-do-código-23-página-26)
17. [Qualidade e Testes (24) — adicionar a auditoria de 05/2026](#17-qualidade-e-testes-24-páginas-27-28)
18. [Segurança da Informação (25) — mover itens de "futuro" pra "implementado"](#18-segurança-da-informação-25-páginas-28-29)
19. [Diagrama ER — REDESENHAR (manual)](#19-diagrama-er-página-20--imagem)

---

## 1. Histórico de Versão (página 4)

**Adicionar uma nova linha no final da tabela:**

| Versão | Período | Fase | Data | Descrição |
|---|---|---|---|---|
| 3.3 | 7º | 03 | 24/05/2026 | Iteração de melhoria geral conduzida com revisão técnica interna. Conformidade LGPD (signed URLs com expiração para arquivos sensíveis) e Res. CFO 226/2020 (trilha de auditoria do prontuário). Correção do bug crítico de salvamento do odontograma. Novos módulos: integração automática plano→faturamento, repasse percentual por dentista, atalho odontograma→plano, termo de consentimento digital com assinatura por canvas. Remoção de telas duplicadas (Onboarding) e código morto. Documentação atualizada (RFs 010–016, RNFs 009–010, RNEs 007–009). |

> 💡 **Bug menor a corrigir de quebra:** a data da v3.0 está como "06/03/2025" — provavelmente deveria ser "06/03/2026", já que está cronologicamente após a v2.3 (25/11/2025).

---

## 2. Descrição do Produto (página 5)

**SUBSTITUIR o parágrafo atual:**

> ~~O ByteDonto é um sistema de gestão odontológica full-stack projetado para centralizar o fluxo clínico e administrativo. A solução oferece módulos de prontuário digital, agendamento inteligente e gestão de clínicas, utilizando Inteligência Artificial para otimizar a retenção de pacientes via WhatsApp. O foco principal é eliminar a dependência de registros manuais e processos fragmentados, garantindo a integridade dos dados e uma comunicação proativa que transforma a jornada do paciente dentro do ambiente odontológico de pequeno e médio porte.~~

**PELO novo texto:**

> O ByteDonto é um sistema de gestão odontológica full-stack projetado para centralizar o fluxo clínico e administrativo. A solução oferece módulos de prontuário eletrônico, odontograma anatômico em notação FDI, plano de tratamento com integração automática ao faturamento, agenda multi-cadeira com check-in, gestão financeira com cálculo de repasse por dentista, e arquivamento digital de termo de consentimento conforme LGPD. O foco principal é eliminar a dependência de registros manuais e processos fragmentados, garantindo a integridade dos dados e a conformidade com as resoluções do Conselho Federal de Odontologia (Res. CFO 226/2020 sobre rastreabilidade do prontuário eletrônico) e da LGPD (Lei nº 13.709/2018, art. 11 sobre dados sensíveis de saúde).

> ⚠️ Removemos "Inteligência Artificial para retenção via WhatsApp" porque essa funcionalidade **não foi entregue** nesta iteração. Continua no backlog.

---

## 3. Resumo do Negócio (página 5)

**SUBSTITUIR o texto atual:**

> ~~...O diferencial competitivo reside na centralização de múltiplas unidades em um único perfil administrativo e no uso de IA para facilitar a comunicação, resolvendo gargalos de agendamento e recuperação de informações clínicas em tempo real.~~

**PELO novo texto:**

> O mercado de gestão odontológica em clínicas menores sofre com a baixa retenção de pacientes, falta de históricos digitais precisos e ausência de integração entre o fluxo clínico e o financeiro. O ByteDonto atua digitalizando a jornada do paciente, da triagem ao pós-atendimento. O diferencial competitivo reside na centralização de múltiplas unidades em um único perfil administrativo, no prontuário digital com auditoria legal completa, e no fluxo clínico-financeiro automatizado (odontograma → plano → cobrança → repasse).

---

## 4. Problemas Identificados (página 5-6)

**Atualizar a tabela:**

| Item | Descrição |
|---|---|
| O problema de | Ineficiência no agendamento, perda de histórico clínico e ausência de integração entre o fluxo clínico e o financeiro. |
| Afeta | Proprietários, Dentistas e Recepcionistas. |
| Cujo impacto é | Baixa retenção de pacientes, erros administrativos, glosas não controladas e perda de cobrança por procedimentos executados. |
| Benefícios de uma solução seriam | Centralização de dados, conformidade legal (LGPD/CFO), automação do ciclo clínico-financeiro e visibilidade de repasse por dentista. |

---

## 5. Situação Atual do Projeto (página 7)

**REESCREVER COMPLETAMENTE.** Substituir o texto atual ("fase inicial de desenvolvimento... apenas landing page e telas de autenticação...") pelo seguinte:

> O ByteDonto atingiu o estado de MVP funcional após a iteração de melhoria geral conduzida em 05/2026. Estão em produção os seguintes módulos:
>
> - Autenticação multi-perfil (Proprietário, Especialista, Recepção) com permissões granulares por chave;
> - Cadastro multi-clínica com vinculação de equipe e edição de papéis;
> - Cadastro completo de pacientes com anamnese obrigatória mínima (alergias, medicações, condições sistêmicas);
> - Agenda semanal com check-in, sala de espera e fluxo de status (Agendado → Aguardando → Finalizado/Cancelado/Faltou);
> - Prontuário clínico com timeline de evolução, receituário imprimível e auditoria por usuário;
> - Odontograma anatômico em SVG por tipo de dente (notação FDI), com painel modal por dente e atalho para o plano de tratamento;
> - Plano de tratamento com itens individualizados e integração automática ao faturamento;
> - Gestão financeira com gráficos mensais, status de pagamento e cálculo de repasse mensal por dentista;
> - Arquivamento de imagens (raio-X, intraoral, laudos) via signed URL com expiração;
> - Termo de consentimento digital (LGPD e procedimento) com assinatura por canvas e arquivamento no prontuário;
> - Trilha de auditoria do prontuário em conformidade com Res. CFO 226/2020.
>
> A iteração de 05/2026 também removeu telas duplicadas (Onboarding, botão Pesquisar redundante, select decorativo), corrigiu o bug crítico do salvamento do odontograma e alinhou enums de pagamento entre frontend e backend.

---

## 6. Objetivos do Semestre (página 7)

**REESCREVER.** Substituir o texto atual:

> Os objetivos do semestre foram em sua maioria atingidos. Restam para as próximas iterações:
>
> - Lembrete automático de consultas via WhatsApp (Evolution API já configurada em `backend/config.py` — falta apenas o agendador);
> - Refinamento da agenda para usar duração real por procedimento e múltiplas cadeiras (campos `duracao_minutos` e `cadeira` já existem no banco);
> - Repasse calculado pela data de pagamento (hoje usa data de criação do lançamento);
> - Vinculação do dentista executor (não apenas do criador do plano) ao lançamento gerado automaticamente;
> - Módulo de convênios e controle de glosa;
> - Recall preventivo automático (limpeza semestral e manutenção mensal de ortodontia);
> - Implementação de testes automatizados (unitários e de integração).

---

## 7. Cronograma do Semestre (páginas 7-8)

**REESCREVER.** Substituir o texto atual:

> O semestre foi organizado em três ciclos. Os marcos abaixo refletem o estado real entregue:
>
> **Ciclo 01 (03/2026):** revisão de arquitetura, padronização de blueprints no backend e refatoração do AuthContext no frontend.
>
> **Ciclo 02 (04/2026):** implementação dos módulos clínicos (prontuário, odontograma, plano de tratamento, receituário, anamnese obrigatória) e dos módulos administrativos (financeiro com gráficos, equipe com permissões granulares).
>
> **Ciclo 03 (05/2026):** revisão técnica geral, com correção de 20 itens envolvendo conformidade LGPD/CFO, bugs críticos (odontograma, enums de cobrança), remoção de código morto e implementação de novas features (integração plano→faturamento, repasse percentual, odontograma→plano, termo de consentimento digital). Atualização documental (v3.3) consolidando todas as mudanças.

---

## 8. Regras de Negócio (páginas 10-12)

**MANTER as RNE-001 a RNE-006 como estão.** **ADICIONAR 3 novas regras:**

### RNE-007
**Descrição:** Toda alteração em prontuário deve ser auditável e dados sensíveis nunca devem ser armazenados como URL pública.
**Requisitos relacionados:** RF-014, RF-015, RF-016, RNF-009
**Detalhamento:** Em conformidade com a Res. CFO 226/2020 (rastreabilidade do prontuário eletrônico) e a LGPD (art. 11 — dados sensíveis de saúde), o sistema registra autor, momento e diff de toda alteração em pacientes, atendimentos e planos; expõe imagens e documentos apenas via signed URL com expiração curta (1 hora), nunca como link público permanente.

### RNE-008
**Descrição:** Item do plano de tratamento marcado como Concluído gera automaticamente cobrança Pendente no faturamento.
**Requisitos relacionados:** RF-010
**Detalhamento:** Quando o dentista conclui um item do plano, o backend gera lançamento financeiro Pendente vinculado ao item (campo `plano_item_id`), com valor, descrição (procedimento + dente) e dentista responsável. Reverter o item para Pendente cancela o lançamento aberto. Operação idempotente.

### RNE-009
**Descrição:** O repasse ao dentista é calculado apenas sobre lançamentos com status Pago no mês de referência.
**Requisitos relacionados:** RF-011
**Detalhamento:** O `percentual_repasse` cadastrado no perfil de cada Especialista é aplicado somente sobre a produção efetivamente paga. Lançamentos Pendentes ou Cancelados não entram no cálculo.

---

## 9. Requisitos Funcionais (páginas 12-13)

### Status que precisa MUDAR

| RF | Status atual no PDF | Status correto |
|---|---|---|
| RF-002 (agendamento) | Em desenvolvimento | **Concluído** |
| RF-004 (cadastro profissionais) | Em desenvolvimento | **Concluído** |
| RF-005 (prontuário clínico) | Em desenvolvimento | **Concluído** |
| RF-006 (agenda por profissional) | Em desenvolvimento | **Concluído** |
| RF-007 (WhatsApp) | Em desenvolvimento | **Em desenvolvimento** (manter — não foi feito) |
| RF-009 (cancelar/reagendar) | Em desenvolvimento | **Concluído** |

### NOVOS requisitos a adicionar

#### RF-010
**Descrição:** O sistema deve vincular automaticamente itens do plano de tratamento ao faturamento.
**Status:** Concluído
**Prioridade:** Alta
**Detalhamento:** Quando um item do plano é marcado como Concluído, o backend cria lançamento Pendente em faturamento com valor, descrição (procedimento + dente) e dentista responsável. Ao reverter para Pendente, o lançamento é cancelado. Operação idempotente.

#### RF-011
**Descrição:** O sistema deve calcular e exibir o repasse mensal devido a cada dentista.
**Status:** Concluído
**Prioridade:** Alta
**Detalhamento:** Endpoint `/api/financeiro/repasses?mes=YYYY-MM` soma lançamentos PAGOS por `dentista_responsavel`, aplica o `percentual_repasse` cadastrado no perfil e devolve relatório consumido pela tela do Owner Financial.

#### RF-012
**Descrição:** O sistema deve oferecer odontograma anatômico interativo em notação FDI.
**Status:** Concluído
**Prioridade:** Alta
**Detalhamento:** Componente SVG dedicado por tipo de dente (incisivo, canino, pré-molar, molar) com curva de arcada, painel modal por dente com chips de estado (Hígido, Cárie, Restaurado, Coroa, Extração Indicada, Ausente, Implante, Selante) e campo de observação. Persiste como JSONB no paciente.

#### RF-013
**Descrição:** O sistema deve atalhar do odontograma para o plano de tratamento.
**Status:** Concluído
**Prioridade:** Média
**Detalhamento:** No painel de edição de um dente, quando o status sugere um procedimento (Cárie → Restauração, Ausente → Implante etc.), um botão abre o formulário de plano de tratamento com dente e procedimento pré-preenchidos.

#### RF-014
**Descrição:** O sistema deve coletar e arquivar termo de consentimento digital (LGPD e procedimento).
**Status:** Concluído
**Prioridade:** Alta
**Detalhamento:** Componente com texto-base de LGPD e consentimento informado de procedimento, captura de assinatura por canvas e arquivamento HTML+assinatura no prontuário (tipo `termo_lgpd` / `termo_consentimento`). Também imprime/salva PDF localmente.

#### RF-015
**Descrição:** O sistema deve registrar trilha de auditoria de alterações no prontuário.
**Status:** Concluído
**Prioridade:** Alta
**Detalhamento:** Toda mudança em pacientes, atendimentos e planos é gravada na tabela `auditoria_prontuario` com usuário, momento, ação (INSERT/UPDATE/DELETE) e diff campo a campo, atendendo à Res. CFO 226/2020.

#### RF-016
**Descrição:** O sistema deve armazenar imagens do paciente protegidas por signed URL com expiração.
**Status:** Concluído
**Prioridade:** Alta
**Detalhamento:** Bucket privado no Supabase Storage. O backend emite signed URL com expiração de 1 hora a cada listagem. Coluna `url` pública removida do schema. Apenas `storage_path` é persistido no banco. Conformidade com LGPD art. 11.

---

## 10. Requisitos Não Funcionais (páginas 13-14)

### ⚠️ Bug de formatação para corrigir

A partir do quinto requisito, a numeração no PDF virou `RF-005`, `RF-006`, `RF-007`, `RF-008`, `RF-009` (parece copy-paste). Deve ser **RNF-005**, **RNF-006**, **RNF-007**, **RNF-008**.

### Lista final correta

| ID | Descrição | Status | Prioridade |
|---|---|---|---|
| RNF-001 | Segurança dos dados sensíveis | Concluído | Alta |
| RNF-002 | Interface responsiva | Concluído | Média |
| RNF-003 | Disponibilidade dos serviços | Em desenvolvimento | Alta |
| RNF-004 | Baixo tempo de resposta | Concluído | Média |
| **RNF-005** | Integridade dos dados | Concluído | Alta |
| **RNF-006** | Escalabilidade | Em desenvolvimento | Média |
| **RNF-007** | Usabilidade simples e intuitiva | Concluído | Alta |
| **RNF-008** | Confiabilidade no armazenamento | Em desenvolvimento | Alta |
| **RNF-009** (NOVO) | Conformidade com LGPD e Res. CFO 226/2020 | Concluído | Alta |
| **RNF-010** (NOVO) | Manutenibilidade e idempotência das migrações SQL | Concluído | Média |

### NOVOS requisitos não funcionais

#### RNF-009
**Descrição:** O sistema deve estar em conformidade com LGPD (Lei 13.709/2018) e Res. CFO 226/2020.
**Status:** Concluído
**Prioridade:** Alta
**Detalhamento:** Implementado: signed URL com expiração para arquivos sensíveis, tabela `auditoria_prontuario` com diff campo a campo, termo de consentimento digital com assinatura por canvas, remoção do fallback inseguro de criação automática de clínica.

#### RNF-010
**Descrição:** O sistema deve permitir manutenção facilitada do código e idempotência das migrações SQL.
**Status:** Concluído
**Prioridade:** Média
**Detalhamento:** Estrutura em camadas (Blueprints Flask, componentes React), princípios SOLID. O script `database_completo.sql` usa `CREATE TABLE IF NOT EXISTS` e `ALTER TABLE ADD COLUMN IF NOT EXISTS`, podendo ser executado múltiplas vezes sem efeitos colaterais.

---

## 11. Modelagem de Dados (página 19)

**REESCREVER o trecho de entidades.** Substituir a lista atual de 4 entidades (clinicas, profissionais, pacientes, agendamentos) pela lista real de **9 entidades**:

> O banco PostgreSQL (gerenciado via Supabase) está estruturado para multi-inquilinato (multi-tenancy) por clínica. As entidades atuais são:
>
> | # | Entidade | Descrição |
> |---|---|---|
> | 1 | `clinicas` | Cadastro da unidade (nome, CNPJ, telefone, endereço JSONB, dono_id). |
> | 2 | `usuarios` | Perfil do membro (Dono, Especialista, Recepção) vinculado a uma clínica, com permissões JSONB, ativo e `percentual_repasse`. |
> | 3 | `pacientes` | Registro pessoal e clínico vinculado a uma clínica. Inclui `anamnese` (JSONB), `odontograma` (JSONB), `updated_by` e `updated_at` para auditoria. |
> | 4 | `atendimentos` | Consulta agendada/realizada. Inclui `duracao_minutos`, `cadeira`, status, evolução clínica, procedimentos descritos, `updated_by`/`updated_at`. |
> | 5 | `faturamento` | Lançamento financeiro com valor, descrição, forma e status de pagamento, dentista responsável e `plano_item_id` (vínculo opcional ao item do plano). |
> | 6 | `planos_tratamento` | Plano de tratamento por paciente com valor total, status (Orçamento, Aprovado, Em Andamento, Concluído, Cancelado) e observações. |
> | 7 | `plano_itens` | Itens individuais do plano (procedimento, dente, quantidade, valor unitário, status). |
> | 8 | `paciente_imagens` | Arquivos do paciente (raio-X, intraoral, laudos, termos). Armazena apenas `storage_path`; URL é gerada sob demanda como signed URL. |
> | 9 | `auditoria_prontuario` | Trilha de auditoria (Res. CFO 226/2020): usuário, ação, tabela, registro, diff campo a campo e timestamp. |

### Relações principais (para o DER)

- `clinicas` 1—N `usuarios`; `clinicas` 1—N `pacientes`; `clinicas` 1—N `atendimentos`; `clinicas` 1—N `faturamento`; `clinicas` 1—N `planos_tratamento`.
- `pacientes` 1—N `atendimentos`; `pacientes` 1—N `faturamento`; `pacientes` 1—N `planos_tratamento`; `pacientes` 1—N `paciente_imagens`.
- `planos_tratamento` 1—N `plano_itens`; `plano_itens` 1—1 `faturamento` (via `plano_item_id`, opcional).
- `usuarios` (Especialista) 1—N `atendimentos` (`dentista_id`); `usuarios` 1—N `faturamento` (`dentista_responsavel`).
- `auditoria_prontuario` referencia `paciente_id`, `usuario_id` e `registro_id` (polimórfico por tabela).

> ⚠️ **Atenção:** o diagrama ER (imagem) precisa ser refeito — hoje está com 4 entidades, são 9.

---

## 12. Estrutura e Manipulação (página 20)

**TROCAR a referência a SQLAlchemy.** Onde está escrito:

> ~~No ByteDonto, a manipulação de dados ocorre de forma centralizada pelo backend Flask utilizando SQLAlchemy ou drivers nativos de conexão com o PostgreSQL do Supabase.~~

**Substituir por:**

> No ByteDonto, a manipulação de dados ocorre de forma centralizada pelo backend Flask utilizando o SDK oficial do Supabase (`supabase-py`, importado como `from supabase import create_client`). A estrutura relacional garante integridade via chaves estrangeiras (`ON DELETE CASCADE` quando apropriado). Combinada com as políticas de RLS, previne o vazamento de dados entre clínicas mesmo na hipótese de a `anon key` vazar — pois o backend acessa via `service_role_key` e o frontend nunca a recebe.

---

## 13. Tecnologias (página 24)

**Esclarecer a hospedagem.** Onde está:

> ~~Hospedagem: GitHub (versionamento) e Vercel (deploy)~~

**Substituir por:**

> Hospedagem:
> - **GitHub** — versionamento do código.
> - **Vercel** — deploy do frontend (React/Vite).
> - **Render** ou **Railway** — deploy do backend (Flask). Vercel não roda Flask nativo.
> - **Supabase** — banco PostgreSQL gerenciado, Auth, Storage e RLS.

---

## 14. Frontend (22.1) (página 25)

**REESCREVER COMPLETAMENTE.** Substituir o texto atual ("principais telas já implementadas incluem a landing page... cadastro de clínica") pelo seguinte:

> O frontend, implementado em React com Vite, está organizado em pastas: `pages` (por perfil — general, owner, specialist, reception), `components` (odontograma, plano, imagens, registro, consentimento etc.), `services` (`api.js` — integração HTTP), `hooks` (`useAuth`, `useSidebar`, `usePermissao`), `context` (`AuthContext`), `routes` (`AppRoutes.jsx`).
>
> **Telas em produção:**
>
> - **Públicas:** Landing, Login (com OAuth Google opcional), Cadastro.
> - **Owner:** ListClinic, ViewClinic, RegisterClinic, EditClinic, BindClinic (equipe + permissões + repasse), Financial.
> - **Specialist:** Dashboard (agenda semanal + grade diária), ListPatients, ViewRecord (timeline, odontograma, plano, anamnese, receituário, imagens).
> - **Reception:** Dashboard (agenda + check-in + sala de espera), ListPatients, ViewPatient (histórico, anamnese, termos de consentimento, arquivos, financeiro), RegisterPatient (com anamnese obrigatória).

---

## 15. Backend (22.2) (página 25)

**REESCREVER.** Substituir o texto atual:

> O backend, em Python com Flask, expõe uma API REST organizada em 9 Blueprints:
>
> - `auth` — registro, login, logout, `/me` (perfil do usuário autenticado).
> - `clinicas` — CRUD de clínicas.
> - `usuarios` — gestão de equipe (criar membro via Supabase Auth Admin, editar nome/papel/percentual_repasse/ativo, ajustar permissões granulares).
> - `pacientes` — CRUD com validadores de CPF/telefone/data, anamnese obrigatória, registro de auditoria.
> - `consultas` — CRUD de atendimentos com validação de status enum, duração e cadeira, registro de auditoria.
> - `financeiro` — CRUD de lançamentos e endpoint `/repasses` (relatório mensal por dentista).
> - `planos` — CRUD de planos de tratamento e itens; PUT de item dispara geração/cancelamento de faturamento.
> - `imagens` — upload/listagem/exclusão, sempre devolvendo signed URL com TTL de 1 hora.
> - `dashboard` — métricas agregadas (pacientes, consultas do dia, receita do mês, pendências).
>
> **Helpers transversais:** `validators.py` (CPF, CNPJ, telefone, data, e-mail, enum), `auditoria.py` (trilha de alterações em prontuário), `database.py` (cliente Supabase compartilhado).

---

## 16. Organização do Código (23) (página 26)

**CORRIGIR a estrutura.** Onde está:

> ~~/backend/app: blueprints (rotas auth, patients), models, utils~~

(não existem pastas `models/` nem `utils/` no projeto)

**Substituir por:**

> A estrutura segue separação por domínio:
>
> - `/frontend/src/pages` — páginas organizadas por papel (general, owner, specialist, reception).
> - `/frontend/src/components` — componentes reutilizáveis (odontograma, plano, registro, imagens, consentimento, bar, footer, section).
> - `/frontend/src/services/api.js` — camada única de integração HTTP com o backend.
> - `/frontend/src/hooks` — `useAuth`, `useSidebar`, `usePermissao`.
> - `/frontend/src/context` — `AuthContext` (sessão + perfil).
> - `/backend/app/<modulo>/routes.py` — cada Blueprint isolado por domínio.
> - `/backend/app/validators.py` — validadores brasileiros (CPF, CNPJ com DV; telefone 10/11 dígitos; e-mail; data).
> - `/backend/app/auditoria.py` — helper de trilha do prontuário.
> - `/backend/app/database.py` — cliente Supabase compartilhado.
> - `/backend/database_completo.sql` — script único e idempotente do schema (CREATE TABLE IF NOT EXISTS + ALTER ADD COLUMN IF NOT EXISTS).
> - `/backend/config.py` — configuração via variáveis de ambiente (Supabase URL/keys, Evolution API para WhatsApp futuro, OpenAI).

---

## 17. Qualidade e Testes (24) (páginas 27-28)

**ADICIONAR um parágrafo** após o trecho sobre smoke tests, antes do parágrafo de "Como evolução, está prevista":

> Adicionalmente, em 05/2026 foi conduzida uma revisão técnica estruturada com 20 itens corrigidos cobrindo conformidade legal (LGPD, CFO 226), bugs críticos (odontograma que não salvava, enums de cobrança incompatíveis, fallback inseguro), remoção de telas duplicadas e implementação de features novas (integração plano→faturamento, repasse por dentista, atalho odontograma→plano, termo de consentimento digital).

---

## 18. Segurança da Informação (25) (páginas 28-29)

### Mover do "futuro" para o "implementado"

A lista de "evolução futura" ainda diz:
> ~~implementação de logs de acesso e auditoria;~~

**Isso já foi feito.** Tirar do "futuro" e adicionar um novo bloco **Implementado** antes da lista de riscos:

> **Implementado na iteração de 05/2026:**
>
> - **Conformidade LGPD (art. 11 — dados sensíveis de saúde):** bucket `paciente-imagens` privado no Supabase Storage; signed URLs com expiração de 1 hora geradas sob demanda; coluna `url` pública removida do schema; apenas `storage_path` é persistido (RF-016, RNF-009).
> - **Conformidade Res. CFO 226/2020 (rastreabilidade do prontuário eletrônico):** tabela `auditoria_prontuario` populada pelo backend a cada INSERT/UPDATE/DELETE em pacientes, atendimentos e planos, registrando autor, momento e diff campo a campo (RF-015, RNF-009).
> - **Termo de consentimento digital (LGPD + procedimento):** assinatura por canvas e arquivamento no prontuário do paciente (RF-014).
> - **Remoção do fallback inseguro** que criava silenciosamente clínica e perfil de usuário em caso de inconsistência: agora retorna HTTP 403 e exige ação explícita do proprietário.

### Atualizar a lista de "evolução futura"

Manter apenas o que **ainda não foi feito:**

> Como evolução futura, estão previstas melhorias como:
>
> - Implementação de rate limiting na rota de login (mitigação de força bruta);
> - Logs estruturados e monitoramento de atividades suspeitas;
> - Políticas de senha mais robustas (complexidade mínima, expiração);
> - Testes de segurança aprofundados (pentest).

---

## 19. Diagrama ER (página 20 — imagem)

**REDESENHAR a imagem.** O diagrama atual mostra apenas 4 entidades (clinicas, profissionais, pacientes, agendamentos). Hoje são **9 entidades** com relações específicas.

### Sugestão de ferramenta
- [dbdiagram.io](https://dbdiagram.io) — exporta DER em PNG/SVG, sintaxe DBML simples
- [draw.io / diagrams.net](https://app.diagrams.net) — gratuito, exporta PNG
- Figma com plugin de diagrama ER

### Código DBML pronto pra colar no dbdiagram.io

```dbml
Table clinicas {
  id uuid [pk]
  nome_fantasia text
  cnpj text
  telefone text
  endereco jsonb
  dono_id uuid
  created_at timestamp
}

Table usuarios {
  id uuid [pk]
  clinica_id uuid [ref: > clinicas.id]
  nome text
  papel text  // Dono | Especialista | Recepção
  permissoes jsonb
  ativo boolean
  percentual_repasse numeric
  created_at timestamp
}

Table pacientes {
  id uuid [pk]
  clinica_id uuid [ref: > clinicas.id]
  nome text
  cpf text
  data_nascimento date
  anamnese jsonb
  odontograma jsonb
  status text
  updated_by uuid [ref: > usuarios.id]
  updated_at timestamp
  created_at timestamp
}

Table atendimentos {
  id uuid [pk]
  clinica_id uuid [ref: > clinicas.id]
  paciente_id uuid [ref: > pacientes.id]
  dentista_id uuid [ref: > usuarios.id]
  data_agendada timestamp
  duracao_minutos int
  cadeira text
  status text
  evolucao_clinica text
  procedimentos_descritos text
  updated_by uuid [ref: > usuarios.id]
  updated_at timestamp
  created_at timestamp
}

Table planos_tratamento {
  id uuid [pk]
  clinica_id uuid [ref: > clinicas.id]
  paciente_id uuid [ref: > pacientes.id]
  dentista_id uuid [ref: > usuarios.id]
  titulo text
  status text
  valor_total decimal
  observacoes text
  created_at timestamp
  updated_at timestamp
}

Table plano_itens {
  id uuid [pk]
  plano_id uuid [ref: > planos_tratamento.id]
  procedimento text
  dente text
  quantidade int
  valor_unitario decimal
  status text  // Pendente | Concluido | Cancelado
  ordem int
}

Table faturamento {
  id uuid [pk]
  clinica_id uuid [ref: > clinicas.id]
  paciente_id uuid [ref: > pacientes.id]
  atendimento_id uuid [ref: > atendimentos.id]
  plano_item_id uuid [ref: > plano_itens.id]
  dentista_responsavel uuid [ref: > usuarios.id]
  valor decimal
  descricao text
  forma_pagamento text
  status_pagamento text  // Pago | Pendente | Cancelado
  created_at timestamp
}

Table paciente_imagens {
  id uuid [pk]
  clinica_id uuid
  paciente_id uuid [ref: > pacientes.id]
  nome text
  storage_path text
  tipo text  // imagem | laudo | termo_lgpd | termo_consentimento
  created_at timestamp
}

Table auditoria_prontuario {
  id bigint [pk]
  clinica_id uuid
  paciente_id uuid
  usuario_id uuid [ref: > usuarios.id]
  tabela text
  registro_id uuid
  acao text  // INSERT | UPDATE | DELETE
  campos jsonb
  created_at timestamp
}
```

---

## ✅ Checklist rápido para o responsável

Use isso como guia ao editar o Google Docs:

- [ ] Adicionar linha v3.3 no histórico (seção 1 deste guia)
- [ ] Corrigir data da v3.0 (provavelmente 2026, não 2025)
- [ ] Reescrever Descrição do Produto (tirar IA/WhatsApp)
- [ ] Atualizar Resumo do Negócio
- [ ] Atualizar Problemas Identificados
- [ ] **REESCREVER** Situação Atual (seção 5)
- [ ] **REESCREVER** Objetivos do Semestre (seção 6)
- [ ] **REESCREVER** Cronograma (seção 7)
- [ ] Adicionar RNE-007, RNE-008, RNE-009
- [ ] Mudar status de RF-002, 004, 005, 006, 009 para Concluído
- [ ] Adicionar RF-010 a RF-016
- [ ] Corrigir numeração de RNF (era RF-005 a RF-009 errado, agora RNF-005 a RNF-008)
- [ ] Adicionar RNF-009 e RNF-010
- [ ] **REESCREVER** Modelagem de Dados (4 → 9 entidades)
- [ ] Tirar referência a SQLAlchemy
- [ ] Esclarecer hospedagem (Vercel = só frontend)
- [ ] **REESCREVER** Frontend (22.1)
- [ ] **REESCREVER** Backend (22.2)
- [ ] **REESCREVER** Organização do Código (23) — sem models/utils
- [ ] Adicionar parágrafo de auditoria em Qualidade e Testes (24)
- [ ] Mover itens já implementados de "evolução futura" para "Implementado" em Segurança (25)
- [ ] **REDESENHAR** o diagrama ER (imagem da página 20) — usar o DBML acima
- [ ] (Opcional) Atualizar protótipos do Figma na seção 16.2

---

*Documento gerado em 24/05/2026 durante a iteração de melhoria geral do ByteDonto.*

# ByteDonto 🦷

Bem-vindo ao repositório do **ByteDonto**! Este repositório é composto por um Front-end (React) e um Back-end (Python/Flask). Este guia ajudará qualquer pessoa da equipe a configurar o ambiente e rodar o projeto localmente de forma simples.

---

## 🛠 1. Pré-requisitos

Para rodar o projeto de ponta a ponta, você vai precisar do **Node.js** (para o front-end) e do **Python** (para o back-end).

### Instalando NVM (Node Version Manager) no Linux / Mac
Para garantir que a equipe toda use a mesma versão do Node, recomendamos instalar através do NVM:

```bash
# 1. Instalar o NVM usando o link oficial do GitHub
curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash

# 2. Carregar o NVM no seu terminal (reinicie o terminal ou rode as linhas que o instalador pedir no final)

# 3. Instalar o Node.js na versão recomendada (20)
nvm install 20

# 4. Selecionar a versão instalada para uso
nvm use 20
```

---

## 🚀 2. Como rodar o projeto

O projeto está dividido em duas pastas: `frontend` e `backend`. É recomendável abrir duas abas no seu terminal para rodar ambos simultaneamente.

### 🖥 Passo 2.1: Rodando o Frontend (React)

Abra a primeira aba no terminal e siga estes passos:

```bash
# Entre na pasta do frontend
cd frontend/

# Instale todas as dependências do projeto
npm install

# Inicie o servidor de desenvolvimento
npm run dev -- --host
```

*(O frontend normalmente será executado em `http://localhost:5173` ou na porta que o Vite indicar no terminal)*

### ⚙️ Passo 2.2: Rodando o Backend (Python/Flask)

Existe **um único backend** (`backend/`). O mesmo código roda na sua máquina e em
produção (Railway); só muda o `.env`, através de `DATA_BACKEND`:

| | `DATA_BACKEND=local` (desenvolvimento) | `DATA_BACKEND=supabase` (produção) |
|---|---|---|
| Banco | PostgreSQL da sua máquina | Supabase Database |
| Login | auth local (JWT) | Supabase Auth (inclui Google) |
| Arquivos | pasta `backend/storage/` | Supabase Storage (bucket privado) |

Abra uma segunda aba no terminal e siga estes passos:

```bash
cd backend/
python3 -m venv venv
source venv/bin/activate          # Windows: .\venv\Scripts\Activate.ps1
pip install -r requirements.txt

cp .env.example .env              # preencha DATABASE_URL, SECRET_KEY e JWT_SECRET (modo local)
python init_db.py                 # cria o banco local e aplica schema + migrations
python seed_demo.py               # (opcional) dados de demonstração — veja as variáveis SEED_*
python run.py                     # API local em http://127.0.0.1:8001 (PORT do .env)
```

O frontend já aponta para a porta 8001 por padrão (proxy do Vite). Detalhes,
variáveis de cada modo, testes e migrations: [`backend/README.md`](backend/README.md).

> A pasta `backend_dev/` é a versão antiga do backend local e foi **substituída**
> pelo modo `DATA_BACKEND=local` do `backend/`. Ela será removida após a validação.

---

## 🤝 Repositório e Contribuição
🔗 **Link do GitHub:** [BitBuilders-UniEvangelica](https://github.com/BitBuilders-UniEvangelica/ByteDonto)

**Atenção para as Variáveis de Ambiente:**  
Tanto o frontend quanto o backend dependem de variáveis sensíveis (`.env` com URLs de banco de dados, chaves de assinatura, etc.). Elas não sobem para o GitHub e **não devem ser trocadas por mensagem**:

- **Desenvolvimento:** copie `backend/.env.example` e `frontend/.env.example` para `.env` e gere as suas próprias chaves (o comando está no próprio exemplo). Cada pessoa usa o seu banco local.
- **Produção:** os segredos ficam só nas variáveis de ambiente do provedor de hospedagem, configuradas pelo painel dele.
- A API **não sobe** sem as chaves obrigatórias, nem com chaves curtas ou de exemplo.

## 🌿 Fluxo de branches

- `main` é o que está publicado; ninguém faz commit direto nele.
- Cada tarefa vai num branch próprio: `feat/…` (funcionalidade), `fix/…` (correção), `chore/…` (manutenção), `test/…` (testes).
- A entrega no `main` é por Pull Request. O CI (`.github/workflows/ci.yml`) roda os testes do backend, o lint do frontend e a auditoria de dependências; o PR só entra com o CI verde.

## 📚 Documentação

- Este README: visão geral e como rodar o projeto.
- `backend/README.md`: detalhes do backend (banco por configuração, testes, migrações).
- `docs/pi/`: notas de trabalho do Documento de Projeto Integrador (não fazem parte do código).
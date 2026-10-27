# backend_dev — API de desenvolvimento (PostgreSQL local)

Cópia do `backend/` para **testes**. Em vez de usar o Supabase, usa o
PostgreSQL instalado na sua máquina. Assim dá para criar, apagar e
quebrar dados à vontade sem encostar nos usuários reais.

| | `backend/` (produção) | `backend_dev/` (desenvolvimento) |
|---|---|---|
| Banco | Supabase | PostgreSQL local (`bytedonto_dev`) |
| Login/senhas | Supabase Auth | tabela `auth.users` local + JWT |
| Imagens/laudos | Supabase Storage | pasta `backend_dev/storage/` |
| Porta | 8000 | **8001** |

Os dois podem rodar ao mesmo tempo.

## 1. Primeira vez

```bash
cd backend_dev
python3 -m venv venv
venv/bin/pip install -r requirements.txt
cp .env.example .env        # depois edite a DATABASE_URL com a senha do seu postgres
venv/bin/python init_db.py  # cria o banco bytedonto_dev e todas as tabelas
venv/bin/python seed_demo.py   # (opcional) clínica, equipe e pacientes de exemplo
```

`DATABASE_URL` no formato `postgresql://USUARIO:SENHA@localhost:5432/bytedonto_dev`.

> Se você não souber a senha do usuário `postgres`, defina uma:
> `sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'nova_senha';"`

## 2. Rodar

```bash
cd backend_dev
venv/bin/python run.py      # http://localhost:8001
```

Para conferir qual backend está respondendo: `http://localhost:8001/api/health`
devolve `"ambiente": "dev (PostgreSQL local)"`.

## 3. Apontar o frontend para o backend certo

O frontend escolhe a API pela variável `VITE_API_URL` (lida em
`src/services/api.js` e `src/components/registro/RegistroClinico.jsx`).
Nenhum código precisa mudar, é só escolher o comando:

```bash
cd frontend
npm run dev         # usa o VITE_API_URL do frontend/.env       -> backend/ (Supabase)
npm run dev:local   # usa o frontend/.env.local-backend          -> backend_dev/ (porta 8001)
```

Como funciona: `npm run dev:local` roda `vite --mode local-backend`. O Vite
carrega primeiro o `.env` e depois o `.env.local-backend`, que sobrescreve só
o `VITE_API_URL`. Para mudar a porta/endereço do backend_dev, edite esse arquivo.

Depois de trocar de backend, **saia e entre de novo** no sistema: o token
salvo no navegador de um backend não vale no outro.

## 4. Zerar o banco de testes

```bash
venv/bin/python init_db.py --reset   # apaga TODOS os dados locais e os arquivos de storage
venv/bin/python seed_demo.py
```

## Diferenças em relação à produção

- **Login com Google não funciona no dev.** Ele é feito direto pelo Supabase no
  frontend; use e-mail e senha.
- Logout invalida o token na hora (no Supabase o token continua válido até expirar).
- Não há confirmação de e-mail nem recuperação de senha por e-mail (o backend
  também não usa isso em produção).

## Levar mudanças do `backend/` para o `backend_dev/`

As rotas são **as mesmas** de produção. Só mudam:

1. `app/database.py` — cliente que imita a API do Supabase usando o PostgreSQL local
   (`.table().select().eq()...`, `auth`, `storage`). Não copie o de produção por cima.
2. `app/storage_local.py` + o registro dele em `app/__init__.py` — entrega dos arquivos.
3. `config.py`, `run.py`, `requirements.txt`.
4. Em `app/auth/routes.py`, `app/usuarios/routes.py`, `app/imagens/routes.py` e
   `seed_demo.py`, a linha `from supabase import create_client` vira
   `from app.database import create_client`.

Então, ao alterar uma rota em `backend/`, copie o arquivo para `backend_dev/` e,
se ele tiver aquele import, troque essa linha. Para conferir:

```bash
diff -r backend/app backend_dev/app -x __pycache__
```

Se criar uma coluna/tabela nova em produção, adicione também em
`database_local.sql` e rode `init_db.py` (ele é idempotente).

## Testes automatizados

Os testes cobrem os fluxos críticos pela própria API (cliente de teste do Flask):

| Arquivo | O que verifica |
|---|---|
| `tests/test_auth.py` | RF-008: registro, login, `/me`, logout e permissões por perfil |
| `tests/test_pacientes.py` | RF-001/RF-003: CPF, anamnese obrigatória e isolamento entre clínicas |
| `tests/test_agenda.py` | RF-002/RF-009: agendamento, check-in, cancelamento e conflito de horário |
| `tests/test_plano_faturamento.py` | RF-010/RNE-008: item concluído gera cobrança, sem duplicar, e reverter cancela |
| `tests/test_repasse.py` | RF-011/RNE-009: repasse só sobre lançamentos pagos |
| `tests/test_esterilizacao.py` | RF-020/RNE-011/RNE-018: ciclos, indicadores e bloqueio de pacotes |

Eles usam um banco **separado**, `bytedonto_test`, que é apagado e recriado a
cada execução a partir do `database_local.sql`. O `bytedonto_dev` não é tocado.

```bash
cd backend_dev
venv/bin/pip install -r requirements-dev.txt
venv/bin/pytest
```

Por padrão a conexão é `postgresql://localhost:5432/bytedonto_test` (usuário do
sistema, sem senha). Se o seu PostgreSQL pede usuário e senha:

```bash
TEST_DATABASE_URL=postgresql://postgres:SENHA@localhost:5432/bytedonto_test venv/bin/pytest
```

O nome do banco precisa terminar em `_test`; caso contrário os testes se recusam
a rodar.

O teste de conflito de horário está marcado como `xfail` (falha esperada): o
RF-002 prevê a validação de sobreposição, mas a rota de agendamento ainda não
faz essa checagem. Quando ela for implementada, o teste passa a acusar
`XPASS` e a marcação deve ser removida.

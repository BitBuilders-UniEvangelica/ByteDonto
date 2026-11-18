# ByteDonto — backend (Flask)

Um único backend para desenvolvimento e produção. O modo de dados é escolhido
por `DATA_BACKEND`; as rotas não sabem qual implementação está por trás.

```
app/
  database.py          ← camada única: escolhe o provider por DATA_BACKEND
  providers/local.py   ← PostgreSQL local (psycopg + pool), auth local, storage em disco
  storage_local.py     ← entrega dos arquivos (registrado só no modo local)
  auth_utils.py        ← RBAC (PERMISSOES_PADRAO), isolamento por clínica, erros
  <módulos>/routes.py  ← auth, pacientes, consultas, planos, imagens, financeiro,
                          dashboard, clínicas, usuários, estoque, esterilização
migrations/*.sql       ← migrations versionadas (as mesmas no Supabase e no local)
database_local.sql     ← schema base do banco local (+ auth local)
init_db.py             ← cria o banco local e aplica schema base + migrations
seed_demo.py           ← dados de demonstração (só modo local)
```

| | `DATA_BACKEND=local` | `DATA_BACKEND=supabase` |
|---|---|---|
| Uso | desenvolvimento e testes | produção (Railway) e homologação |
| Banco | PostgreSQL da máquina (`psycopg` + pool) | Supabase Database (PostgREST) |
| Auth | `auth.users`/`auth.sessions` locais + JWT (`JWT_SECRET`) | Supabase Auth (inclui login com Google) |
| Arquivos | `STORAGE_DIR` + `/api/storage` com link assinado | Supabase Storage, bucket privado, signed URL de 1h |
| Operações atômicas | funções SQL via `.rpc()` | as mesmas funções SQL via `.rpc()` |

## Travas entre ambientes (`config.validar_config`)

A API **não inicia** se:

- `APP_ENV=production` (ou rodando no Railway) com `DATA_BACKEND=local`;
- `DATA_BACKEND=supabase` com `APP_ENV` fora de `production`/`staging`/`homologacao`
  (um `.env` de desenvolvimento com credenciais copiadas de produção não conecta na produção);
- `DATA_BACKEND` ausente fora de produção (em produção o padrão é `supabase`, então o
  Railway continua funcionando sem variável nova);
- no modo local, `DATABASE_URL` não for da própria máquina (`localhost`, `127.0.0.1`,
  socket Unix ou hosts listados em `LOCAL_DB_ALLOWED_HOSTS`) ou citar Supabase,
  pooler, Railway, RDS etc. O provider local repete essa checagem ao abrir o pool;
- `SECRET_KEY` (e, no modo local, `JWT_SECRET`) estiver ausente, for curta (< 32) ou um
  valor padrão conhecido.

## Rodar localmente

```bash
cd backend
python3 -m venv venv && venv/bin/pip install -r requirements.txt
cp .env.example .env    # APP_ENV=development, DATA_BACKEND=local, DATABASE_URL, SECRET_KEY, JWT_SECRET
venv/bin/python init_db.py            # cria o banco e aplica database_local.sql + migrations/*.sql
venv/bin/python seed_demo.py          # opcional (variáveis SEED_* do .env)
venv/bin/python run.py                # http://localhost:8001 (PORT=8001)
```

`init_db.py --reset` apaga o banco local e os arquivos de `STORAGE_DIR`.
Quem já tinha o banco do antigo `backend_dev` (`bytedonto_dev`) só precisa rodar
`init_db.py` uma vez: ele é idempotente e acrescenta as funções, triggers e RLS da migration.

Frontend: `npm run dev` já usa o proxy para `http://localhost:8001`.
O login com Google só existe no modo `supabase`; no local use e-mail e senha.

## Variáveis de ambiente

| Variável | local | supabase | Observação |
|---|---|---|---|
| `APP_ENV` | `development` | `production` / `staging` / `homologacao` | No Railway, vazio = production |
| `DATA_BACKEND` | `local` | `supabase` | Obrigatória fora de produção |
| `SECRET_KEY` | obrigatória | obrigatória | ≥ 32 caracteres aleatórios |
| `DATABASE_URL` | obrigatória | — | só PostgreSQL local |
| `JWT_SECRET` | obrigatória | — | ≥ 32 caracteres; assina tokens e links locais |
| `STORAGE_DIR` | opcional | — | padrão `backend/storage` |
| `LOCAL_DB_ALLOWED_HOSTS` | opcional | — | ex.: `db` (docker compose) |
| `JWT_EXPIRES_SECONDS`, `PUBLIC_API_URL` | opcionais | — | |
| `SUPABASE_URL`, `SUPABASE_KEY`, `SUPABASE_ANON_KEY` | — (ignoradas) | obrigatórias | service role ≠ anon |
| `ALLOWED_ORIGINS`, `PORT`, `RATELIMIT_STORAGE_URI` | opcionais | opcionais | |

## Testes

```bash
venv/bin/pip install -r requirements-dev.txt
TEST_DATABASE_URL=postgresql://USUARIO:SENHA@localhost:5432/bytedonto_test venv/bin/python -m pytest
```

Os testes usam a **implementação real**: `create_app()`, rotas, RBAC, validações e a
camada de dados no modo local, com PostgreSQL real, auth local real e storage real.

| Pasta / marcador | O que cobre |
|---|---|
| `tests/unit` (`-m unit`) | configuração e travas, camada de dados, MIME, regras puras, travas do seed |
| `tests/integracao` (`-m integracao`) | app + PostgreSQL real |
| `-m rotas` | auth, cadastro, erros sem vazamento, pacientes, agenda, planos, repasse, uploads, seed, contrato com o frontend |
| `-m rbac` | matriz papel × rota (403 sem alterar dados), dados ocultos, permissões do Dono |
| `-m isolamento` | clínica A × B em todos os módulos, IDOR no corpo, trigger no banco |
| `-m estoque` / `-m esterilizacao` | regras dos módulos e concorrência real (threads) |
| `-m migrations` | migration aplicada num PostgreSQL que imita o Supabase (papéis, grants, RLS) |

Travas: o banco precisa terminar em `_test` e ser local; ele é recriado a cada execução.
O teste de migrations cria temporariamente `<nome>_rls_test` e os papéis
`anon`/`authenticated`/`service_role` (se não existirem) e remove tudo ao final.

## Migrations no Supabase

`migrations/0001_estoque_esterilizacao.sql` é aditiva e idempotente (só `IF NOT EXISTS`,
`CREATE OR REPLACE`, `DROP POLICY/TRIGGER IF EXISTS` + `CREATE`). Ela cria:

- as 7 tabelas de estoque e esterilização;
- as funções atômicas `estoque_registrar_entrada` / `estoque_registrar_saida`;
- os triggers `garantir_mesma_clinica`, que recusam referências entre clínicas;
- RLS habilitado + policy `sem_acesso_direto` (RESTRICTIVE, nega tudo) + `REVOKE` de
  `anon`/`authenticated` nas tabelas e funções. Só a API (service role) acessa.

Aplicação: **primeiro num projeto de homologação**. Use o SQL Editor ou
`psql "$CONEXAO" -f migrations/0001_estoque_esterilizacao.sql`. Depois confira:

```sql
SELECT relname, relrowsecurity FROM pg_class WHERE relname LIKE '%estoque%' OR relname LIKE '%esteriliz%';
SELECT tablename, policyname, permissive, roles FROM pg_policies WHERE policyname IN ('sem_acesso_direto','api_servidor');
```

# Módulo de esterilização — contrato da API (RF-020)

Registro dos ciclos de esterilização com parâmetros e indicadores, e dos
pacotes produzidos em cada ciclo, conforme a RDC Anvisa nº 1.002/2025.

Prefixo: `/api/esterilizacao` · Header: `Authorization: Bearer <token>`
Permissão: chave `esterilizacao` (Dono sempre; Especialista por padrão;
Recepção só se o Dono liberar).

## Regras

| Regra | Comportamento |
|---|---|
| Resultado do ciclo | Qualquer indicador `Reprovado` reprova. Químico `Aprovado` + biológico `Aprovado` ou `Não realizado` aprova. O resto fica `Pendente`. |
| Estado do pacote | Ciclo pendente: `Aguardando liberação`. Aprovado: `Disponível`. Reprovado: `Bloqueado`. Disponível com a data limite vencida é devolvido como `Vencido`. |
| RNE-011 | Indicador reprovado bloqueia **todos** os pacotes do ciclo, inclusive os já liberados. Ciclo reprovado não pode ser reaprovado nem receber pacotes (409). |
| RNE-018 | Não existe exclusão. Equipamento é inativado (`ativo: false`); ciclos e pacotes ficam preservados. |
| Numeração | `numero_ciclo` é sequencial por equipamento. Código do pacote: `<equipamento>-C<ciclo>-P<seq>`, ex. `AC01-C0012-P03`. |

## Rotas

### Equipamentos
- `GET /equipamentos`: ativos. Com `?todos=1`, inclui os inativos.
- `POST /equipamentos`: `{ identificacao*, tipo?, fabricante?, modelo?, numero_serie? }` → 201 (409 se a identificação já existe na clínica).
- `PUT /equipamentos/<id>`: mesmos campos + `ativo` (bool).

### Ciclos
- `GET /ciclos`: filtros `?equipamento_id=` e `?resultado=`. Inclui `equipamento.identificacao` e `responsavel.nome`.
- `POST /ciclos` → 201, devolve o ciclo com `pacotes`.
  ```json
  {
    "equipamento_id": "uuid",
    "iniciado_em": "2026-10-27T08:00:00",
    "temperatura_c": 134,
    "pressao_kgf_cm2": 2.1,
    "tempo_exposicao_min": 7,
    "indicador_quimico": "Aprovado",
    "indicador_biologico": "Pendente",
    "observacoes": "opcional",
    "pacotes": [
      { "conteudo": "Kit clínico", "validade_dias": 30 },
      { "conteudo": "Kit cirúrgico", "data_limite_uso": "2026-11-26", "metodo": "opcional" }
    ]
  }
  ```
  Limites: temperatura 100–200 °C, pressão 0,1–5 kgf/cm², tempo 1–240 min,
  validade 1–365 dias. Indicadores: químico `Aprovado | Reprovado | Pendente`;
  biológico `Aprovado | Reprovado | Pendente | Não realizado`. Cada pacote
  precisa de `conteudo` e de `validade_dias` **ou** `data_limite_uso`.
- `GET /ciclos/<id>`: ciclo com a lista de pacotes.
- `PUT /ciclos/<id>/indicadores`: `{ indicador_quimico?, indicador_biologico?, observacoes? }`. Recalcula o resultado e atualiza os pacotes. Devolve 409 se o ciclo já foi reprovado.
- `POST /ciclos/<id>/pacotes`: `{ pacotes: [...] }` → 201 com os pacotes criados.

### Pacotes
- `GET /pacotes`: filtros `?ciclo_id=`, `?estado=` (incluindo `Vencido`) e
  `?disponiveis=1` (só os utilizáveis hoje, para o RF-021).

## Banco

Tabelas `equipamentos_esterilizacao`, `ciclos_esterilizacao` e
`pacotes_esterilizados` em `database_local.sql`. Para criar no banco local:
`venv/bin/python init_db.py` (é idempotente e não apaga dados).

Testes: `tests/test_esterilizacao.py` (13 testes).

## Próximo passo

RF-021: vincular o pacote ao atendimento (tabela `pacote_uso`). Isso permite
listar os pacientes afetados quando um ciclo é reprovado, completando a RNE-011.

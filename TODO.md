# TODO

Próximos passos planejados. Contexto do projeto em [AGENTS.md](AGENTS.md).

## Refatoração: camada de serviço compartilhada — concluída (terminal)

`main.py` mistura três coisas: o loop de terminal, a lógica de montar/persistir mensagens e a
invocação do grafo. Isso travava a criação de TUI e API, porque as duas precisariam duplicar essa
lógica. Extraído pra um módulo compartilhado (`chat/`), usado igualmente por CLI, TUI e API.
`main.py` virou um dispatcher puro (`python main.py terminal|tui|api`).

**Nome do módulo:** ficou `chat/` (em vez do `agent_flow/` provisório do rascunho original) — evita
colisão de vocabulário com `graph/` (já é o "flow" do LangGraph) e `agents/` (já é "agent"), e casa
com o nome que a collection do Mongo já usa (`tools/mongo/chats`).

Estrutura implementada:

```text
chat/
├── models.py          # ChatMessage, Role — contrato interno, independente de Mongo/tool
├── repositories.py    # acesso a tools/mongo/chats, tools/mongo/users e tools/postgres/users
├── runner.py           # chama fluxo_agentes.invoke (graph/builder.py) e extrai a resposta
└── service.py          # create_chat(), send_message(), get_history(), encerrar_sessao()

interfaces/
├── terminal/
│   ├── app.py           # run() — loop de input() do terminal, usando chat.service
│   └── display.py        # Rich + pyfiglet (era ui/terminal.py, absorvido aqui)
├── tui/
│   └── app.py           # vazio — ver "TUI com Textual" abaixo
└── api/
    └── app.py           # vazio — ver "API" abaixo
```

- [x] `chat/models.py`, `chat/repositories.py`, `chat/runner.py`, `chat/service.py`
- [x] `interfaces/terminal/app.py` + `interfaces/terminal/display.py` — `ui/terminal.py` foi
      absorvido aqui (só era consumido pelo terminal; TUI vai usar widgets Textual, não Rich)
- [x] `main.py` reescrito como dispatcher puro — `terminal` funcional, `tui`/`api` imprimem
      "ainda não implementado" e saem (os arquivos `interfaces/{tui,api}/app.py` ficam vazios até
      as seções abaixo saírem do papel)
- [ ] `interfaces/tui/app.py` — ver checklist da seção "TUI com Textual" abaixo
- [ ] `interfaces/api/app.py` — ver checklist da seção "API" abaixo

Verificado: `python main.py terminal` ponta a ponta via stdin (mensagem real → guardrail → router →
financeiro → resposta → resumo de sessão + atualização de perfil no `/exit`), comportamento
idêntico ao `main.py` antigo.

Fluxo da API quando sair do papel:

```text
HTTP request
  -> autenticação
  -> identifica user_id pelo token
  -> valida ownership do chat
  -> chat.service.send_message(...)
       -> carrega histórico (chat.repositories)
       -> executa o agente (chat.runner)
       -> persiste mensagem do usuário e resposta (chat.repositories)
  -> retorna resposta
```

## Alembic para PostgreSQL

Hoje não existe tabela de usuário no Postgres — `user_id` é só uma string gerada em `main.py`
(`uuid4()`, mockado) e o cadastro "de verdade" mora inteiro no Mongo (`tools/mongo/users`).
Sem uma tabela de usuário no Postgres, transações e eventos (`tools/postgres/financeiro`,
`tools/postgres/agenda`) não têm de fato uma FK confiável para `user_id`.

- [x] Adicionar `alembic` às dependências (`uv add alembic`) e rodar `alembic init`
- [x] Migration inicial (`1ae7bbffb913_baseline_schema.py`) cobrindo o schema atual (transações,
      eventos, categorias) que já existia no Postgres fora de migration — banco de dev marcado
      com `alembic stamp` nessa revisão em vez de recriado
- [x] Tabela `users` enxuta (`28948ff7767a_add_users_table.py`) — só `id` (mesmo UUID já usado como
      `user_id` no Mongo) e `created_at`; dados "valiosos" de perfil continuam só no Mongo
- [x] Decidir o identificador comum entre Postgres e Mongo — reusar o mesmo UUID nos dois em vez de
      IDs desacoplados (confirmado no comentário da migration `28948ff7767a`)
- [x] FK de `transactions`/`events` para `users.id` (`a83e50c95f94_add_user_id_fk_to_transactions_and_.py`)
      — coluna `user_id` NOT NULL com backfill para um usuário "legado"
      (`00000000-0000-0000-0000-000000000001`) e `DEFAULT` para esse mesmo usuário, já que
      `add_transaction`/`add_event` ainda não passam `user_id` explícito (ver follow-up abaixo)
- [x] Garantir que a criação do usuário no Mongo (`users.garantir_usuario`) e o insert em `users` do
      Postgres (`tools/postgres/users/core.py:garantir_usuario`) aconteçam juntos — ambos chamados
      em `main.py` com o mesmo `user_id`
- [x] Documentar o comando de migration no README (`alembic upgrade head`)

**Follow-up (fora do escopo do que foi feito acima):** `add_transaction`, `query_transactions`,
`update_transaction`, `add_event`, `query_daily_events`, `query_events`, `update_event` ainda não
gravam nem filtram por `user_id` real — todo INSERT novo cai no usuário legado via `DEFAULT` da
coluna. Propagar o `user_id` do agente por essas tools e então remover o `DEFAULT` da coluna.

## ORM (SQLAlchemy) — concluído

`tools/postgres/*` migrou de `psycopg2` cru pra SQLAlchemy ORM.

- [x] Models declarativos em `tools/postgres/models.py` (`User`, `TransactionType`, `Category`,
      `Transaction`, `Event`) — mapeiam o schema existente 1:1, incluindo os índices já criados
      pelas migrations (`idx_transactions_occurred_at`, `idx_transactions_category_time`,
      `idx_transactions_localday` — este último como expressão via `text()` pra bater
      exatamente com o índice reflectido) e o `ondelete="SET NULL"` da FK de categoria
- [x] `tools/postgres/connection.py` trocou `ThreadedConnectionPool` por `Engine`/`sessionmaker`;
      `get_session()` já faz `commit()`/`rollback()` automático (tools não chamam mais isso na mão)
- [x] `tools/postgres/financeiro/core.py` e `agenda/core.py` reescritas tool por tool, preservando
      exatamente o mesmo dict de retorno (`Response.ok`/`Response.error`) e o `try/except` em volta
      de cada tool — necessário porque `log_tool` não captura exceção nenhuma, só inspeciona
      `result["status"]`
- [x] `tools/postgres/helpers.py`: `resolve_type_id`/`get_category_id` via `select()`;
      `local_date_filter_sql` virou `local_date`/`local_date_filter`/`local_date_range_filter`
      (expressões SQLAlchemy reutilizáveis, unificando um filtro de timezone que antes estava
      duplicado inline em três lugares de `agenda/core.py`)
- [x] `tools/postgres/users/core.py`: `garantir_usuario` agora usa
      `insert(...).on_conflict_do_nothing()` do dialeto Postgres, preservando a idempotência
- [x] `alembic/env.py` com `target_metadata = Base.metadata` — `--autogenerate` funciona a partir
      de agora (verificado: diff vazio contra o schema real após os ajustes de tipo/índice/FK)

**Achado durante a migration:** diferente do SQL cru (que omite a coluna e deixa o Postgres aplicar
o `DEFAULT`), o SQLAlchemy ORM sempre manda a coluna no `INSERT`, incluindo `NULL` explícito pra
atributos não setados — isso quebrava o `DEFAULT` do usuário legado (`user_id`) até adicionar um
`default=LEGACY_USER_ID` do lado Python em `Transaction`/`Event` (`tools/postgres/models.py`).
Continua valendo o follow-up de propagar `user_id` real, registrado na seção Alembic acima.

## Redis

`redis` já está em `pyproject.toml` mas nenhuma tool usa ainda.

- [ ] `tools/redis/connection.py` — client lazy (init só no primeiro uso, seguindo o padrão de
      `tools/postgres/connection.py` e `tools/mongo/connection.py`)
- [ ] Cache de sessão: mover/duplicar o histórico curto de mensagens (hoje via `$slice: -5` no
      Mongo) para Redis, com TTL, reduzindo round-trip ao Mongo em cada turno
- [ ] Cache de `perfil_usuario` (hoje lido do Mongo a cada invocação em `main.py:executar_fluxo_assessor`)
- [ ] Rate limit / cooldown do guardrail de entrada por `user_id`
- [ ] Variável de ambiente `REDIS_URI` em `.env.example` e `config/settings.py`

## Qdrant

Hoje o RAG do FAQ usa FAISS local (`tools/faq_tools.py`). Avaliar migração para Qdrant quando
precisar de mais de um documento/coleção ou busca persistente fora de memória.

- [ ] `tools/qdrant/connection.py` — client lazy
- [ ] `tools/qdrant/faq/core.py` — reimplementar `faq_retriever` sobre Qdrant (collection por domínio,
      ex. `faq`, e futuramente `financeiro`/`agenda` para busca semântica sobre histórico)
- [ ] Script de ingestão dos PDFs de `data/documents/` para a collection do Qdrant
- [ ] Decidir: Qdrant local (Docker, mesmo padrão do `config/docker.py`) vs. Qdrant Cloud
- [ ] Variáveis `QDRANT_URL` / `QDRANT_API_KEY`

## API

Hoje só existe o loop de terminal em `main.py`. Expor o fluxo via API para permitir outros clientes
(TUI, frontend, integrações). Depende da refatoração acima — a API é só mais uma interface sobre
`chat.service`, não deve chamar `graph/builder.py` direto.

- [ ] Escolher framework (FastAPI é o caminho natural dado o resto do stack Python async)
- [ ] `interfaces/api/app.py` com endpoint `POST /chats/{chat_id}/messages` chamando
      `chat.service.send_message(...)` e retornando a resposta
- [ ] Endpoint de streaming (SSE ou WS) para respostas incrementais do LangGraph
- [ ] Autenticação por token, identificando `user_id` a partir dele (hoje é mockado em `main.py`) e
      validando ownership do chat antes de chamar o service
- [ ] Dockerfile + healthcheck

## TUI com Textual

Substituir/complementar a interface atual (`ui/terminal.py`, Rich + pyfiglet) por uma TUI de
verdade com [Textual](https://github.com/Textualize/textual).

- [ ] Adicionar `textual` às dependências (`uv add textual`)
- [ ] `interfaces/tui/app.py` — `AssessorTUI`, App Textual com tela de chat (input fixo embaixo,
      histórico rolável), chamando `chat.service.send_message(...)` — nunca `graph/builder.py` direto
- [ ] Widget de histórico com bolhas usuário/assistente reaproveitando a lógica de
      `exibir_usuario`/`exibir_assistente` de `ui/terminal.py`
- [ ] Indicador de "pensando..." enquanto o agente processa (rodar `chat.service.send_message` em
      thread/worker do Textual para não travar a UI)
- [ ] Tela/painel lateral opcional mostrando qual agente está ativo (`agentes_chamados` do estado)
- [ ] Comando `/exit` e `Ctrl+C` encerrando a sessão via `chat.service`

## Débitos técnicos / melhorias soltas

- [ ] Transformar as tabelas de `types` (`tools/postgres/models.py:TransactionType`, hoje resolvida
      via `resolve_type_id` em `tools/postgres/helpers.py`) em `enum` Python + `type` `payment_types`
      no lugar de linhas em tabela consultadas em runtime
- [ ] `[project.scripts]` no `pyproject.toml` para rodar `assessor` (comando instalado) em vez de
      `uv run main.py <args>`
- [ ] Adicionar checagem de tipagem estática com **mypy** (ruff cobre lint/format mas não faz type
      checking; mypy é o que de fato valida as anotações de tipo) — avaliar `strict` vs. modo
      incremental dado que o projeto ainda não tem nenhuma tipagem checada

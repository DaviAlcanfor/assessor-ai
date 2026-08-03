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

## Redis — estrutura concluída, integrações pendentes

Split em `tools/redis/{connection.py,api_key.py,chat.py,schemas.py}` feito, seguindo o mesmo corte
de `tools/postgres` e `tools/mongo`.

- [x] Client lazy (`tools/redis/connection.py:get_client`)
- [x] Extrair a conexão para `tools/redis/connection.py`, deixando `api_key.py`/`chat.py` só com as
      tools
- [x] Rate limit / cooldown por `user_id` (`can_send_message`, `tools/redis/chat.py:8`) — mas
      **ainda não é chamado em lugar nenhum** (nem no guardrail de entrada, nem nas rotas da API;
      as rotas usam `slowapi` por IP via `@limiter.limit(...)`, que é um mecanismo separado)
- [ ] Alocação de API key por usuário (`allocate_api_key`/`get_user_id_by_api_key`,
      `tools/redis/api_key.py`) — implementado e já consumido em leitura por
      `interfaces/api/auth.py:get_current_user`, mas **nada chama `allocate_api_key` ainda**:
      `interfaces/api/gen_key.py:generate_api_key` só gera a string, não persiste no Redis
- [ ] Cache de sessão: mover/duplicar o histórico curto de mensagens (hoje via `$slice: -5` no
      Mongo) para Redis, com TTL, reduzindo round-trip ao Mongo em cada turno
- [ ] Cache de `perfil_usuario` (hoje lido do Mongo a cada invocação em `main.py:executar_fluxo_assessor`)

## Qdrant — conexão criada, tools ainda não

Hoje o RAG do FAQ usa FAISS local (`tools/faq_tools.py`). Avaliar migração para Qdrant quando
precisar de mais de um documento/coleção ou busca persistente fora de memória.

- [x] `tools/qdrant/connection.py` — client assíncrono lazy (`get_qdrant_client`, generator
      `yield`/`close` pra uso como dependency do FastAPI)
- [x] Variáveis `QDRANT_URL` / `QDRANT_API_KEY` no `.env.example`
- [ ] `tools/qdrant/faq/core.py` — reimplementar `faq_retriever` sobre Qdrant (collection por domínio,
      ex. `faq`, e futuramente `financeiro`/`agenda` para busca semântica sobre histórico)
- [ ] Script de ingestão dos PDFs de `data/documents/` para a collection do Qdrant
- [ ] Decidir: Qdrant local (Docker, mesmo padrão do `docker-compose.yml`) vs. Qdrant Cloud — hoje
      o compose já sobe `qdrant/qdrant:latest` local

## API — endpoints de chat funcionando, faltam streaming e infra

Saiu do esqueleto: `interfaces/api/main.py` registra `health_router` e `chats_router` de verdade,
com autenticação por API key (`X-API-Key` via `interfaces/api/auth.py`) e rate limiting por IP
(`slowapi`, `interfaces/api/rate_limiting.py`). `main.py api` (o dispatcher do CLI) ainda não sobe
esse app — continua imprimindo "ainda não implementado"; hoje a API roda direto via uvicorn.

- [x] Escolher framework — FastAPI
- [x] Esqueleto de pastas — virou `interfaces/api/{main,auth,gen_key,rate_limiting}.py` +
      `routes/{chats,health}.py` + `schemas/chat.py` (não `app/` como o TODO antigo previa)
- [x] `auth.py` — `get_current_user` via `APIKeyHeader` + `tools/redis/api_key.py:get_user_id_by_api_key`
- [x] `routes/chats.py` — `POST /v1/chats` (cria chat) e `POST /v1/chats/{chat_id}/messages`
      chamando `chat.service.send_message(...)`
- [x] `routes/health.py` — `/health/live` e `/health/ready` (ping no Redis)
- [x] Rate limiting por IP nas rotas de chat (`slowapi`, 5/min criar chat, 10/min mensagem)
- [ ] `gen_key.py:generate_api_key` gerar **e persistir** a key via
      `tools/redis/api_key.py:allocate_api_key` (hoje as duas funções existem mas não se conectam —
      não tem endpoint/script que de fato emite uma key utilizável)
- [ ] Validar ownership do chat antes de `send_message` (hoje qualquer `user_id` autenticado pode
      mandar mensagem pra qualquer `chat_id`, sem checar se o chat pertence a ele)
- [ ] Endpoint de streaming (SSE ou WS) para respostas incrementais do LangGraph
- [ ] Ligar `main.py api` ao app de `interfaces/api/main.py` (hoje é só um stub que imprime e sai)
- [ ] Dockerfile + healthcheck (compose hoje só sobe a infra — postgres/mongo/redis/qdrant —, não a
      própria API)

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

## Testes

Hoje não existe suíte de testes (ver AGENTS.md). Criar pasta `tests/` espelhando a estrutura de
`tools/`, `chat/`, `agents/`, `graph/` (package by feature, mesmo corte usado no resto do repo).

- [ ] Adicionar `pytest` (e `pytest-mock`/`pytest-asyncio` se necessário) como dev dependency
      (`uv add --dev pytest`)
- [ ] `tests/conftest.py` com fixtures compartilhadas — provavelmente mocks de
      `tools/postgres/connection.py:get_session` e `tools/mongo/connection.py` pra não depender de
      banco real nos testes unitários
- [ ] `tests/tools/` — começar pelo mais isolado e sem I/O: `tools/response.py` (`Response.ok`/`Response.error`),
      `tools/postgres/helpers.py` (resolve_transaction_type, local_date/local_date_filter), `tools/redis/schemas.py`
      (`_chave_mensagem`/`_chave_api_key`)
- [ ] `tests/chat/` — `chat/service.py` e `chat/runner.py` com o grafo mockado (não deve chamar
      LLM de verdade em teste unitário)
- [ ] Decidir separação `tests/unit/` vs. `tests/integration/` (integration = sobe Postgres/Mongo
      via `config/docker.py`) antes de crescer demais, ou manter achatado enquanto a suíte for pequena
- [ ] CI (GitHub Actions) rodando `pytest` no PR, uma vez que exista massa crítica de testes

## Débitos técnicos / melhorias soltas

- [x] Transformar as tabelas de `types` em `enum` Python + tipo nativo do Postgres — `TransactionType`
      e `PaymentType` (`tools/postgres/models.py`) agora são `StrEnum` mapeados pra `SAEnum(...,
      create_type=False)` sobre os tipos `transaction_type`/`payment_type` já criados via migration
      (`..._transaction_type_and_payment_type_as_...py`); `resolve_type_id` virou
      `resolve_transaction_type`, puramente em Python (`tools/postgres/helpers.py`)
- [x] `ruff` (lint + format) adicionado e aplicado no repo (`dd09c43`, `c95365c`) — ver
      `ruff check` pendente: `PLE0604` em `agents/prompts/__init__.py` (bug real, `__all__` com
      classes em vez de strings) e alguns `BLE001`/`PLW1510` que ficaram de fora do `--fix` por
      exigirem decisão manual
- [x] `[project.scripts]` no `pyproject.toml` — `assessor-ai = 'main:main'`
- [ ] Adicionar checagem de tipagem estática com **mypy** (ruff cobre lint/format mas não faz type
      checking; mypy é o que de fato valida as anotações de tipo) — avaliar `strict` vs. modo
      incremental dado que o projeto ainda não tem nenhuma tipagem checada
- [ ] Corrigir `PLE0604` em `agents/prompts/__init__.py` — `__all__` referencia as classes
      (`RouterPrompts`, `FinanceiroPrompts`, ...) em vez dos nomes como string
- [ ] `config/settings.py` está dessincronizado do `.env.example` pós-migração pra Docker Compose:
      settings pede `POSTGRES_URL`, `MONGO_USER`/`MONGO_PASSWORD`/`MONGO_URL`/`MONGO_COLLECTION_NAME`,
      `UPSTASH_REDIS_REST_URL`/`UPSTASH_REDIS_REST_TOKEN`, `QDRANT_CLUSTER_ENDPOINT`; o
      `.env.example` documenta `POSTGRES_URI`, `MONGODB_URI`, `REDIS_URI`, `QDRANT_URL` — nomes
      diferentes. Como são campos obrigatórios do `pydantic-settings` (sem default), subir a app só
      com o `.env.example` como guia falha na validação — precisa alinhar um lado pro outro

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
- [x] `interfaces/tui/app.py` — ver checklist da seção "TUI com Textual" abaixo
- [x] `interfaces/api/app.py` (na prática virou `interfaces/api/main.py`) — ver checklist da seção
      "API" abaixo

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

- [x] **Follow-up:** `add_transaction`, `query_transactions`, `update_transaction`, `add_event`,
      `query_daily_events`, `query_events`, `update_event` passaram a gravar e filtrar pelo `user_id`
      real. Como as tools são invocadas pelo LLM via tool-calling (args escolhidos por ele) e o
      `Estado` do LangGraph não carrega `user_id`, a propagação usa um `contextvars.ContextVar`
      (`tools/postgres/connection.py:current_user_id`/`set_current_user`/`reset_current_user`),
      setado uma vez por request em `chat/runner.py:executar` (a partir do `user_id` já conhecido em
      `chat/service.py:send_message`) e lido dentro de cada tool — nunca exposto como argumento pro
      LLM. `update_transaction`/`update_event` por `id` direto agora checam ownership (`tx.user_id ==
      current_user_id()`), tratando registro de outro usuário como "não encontrado" (mesma resposta
      de id inexistente, não vaza a existência do registro).

**Segue pendente (fora do escopo acima):** a coluna `user_id` continua com `DEFAULT`/
`LEGACY_USER_ID` como rede de segurança — remover o `DEFAULT` via migration é um passo separado,
só depois de garantir que todo caminho de insert sempre tem `user_id` do contexto.

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

- [x] Client lazy (`tools/redis/connection.py:get_client`) — **achado:** faltava o `_client: Redis |
      None = None` no module scope, então `get_client()` quebrava com `NameError` na primeira
      chamada; ficou mascarado porque todo chamador está dentro de um `except Exception` genérico.
      Corrigido.
- [x] Extrair a conexão para `tools/redis/connection.py`, deixando `api_key.py`/`chat.py` só com as
      tools
- [x] Rate limit / cooldown por `user_id` (`can_send_message`, `tools/redis/chat.py:8`) chamado em
      `chat/service.py:send_message` — não no nó de guardrail do LangGraph (`Estado`, o TypedDict do
      grafo, não carrega `user_id` hoje, e enfiar isso lá só pra checar um contador do Redis seria
      complexidade desnecessária). `send_message` é o único ponto por onde terminal, TUI e API
      passam, então cobre as três interfaces de uma vez. Estourar o limite levanta
      `LimiteDeMensagensExcedido` (nova, `chat/service.py`); `routes/chats.py` traduz isso pra `429`
      antes do catch-all genérico que vira `500`. Continua complementar ao `slowapi` por IP das
      rotas — mecanismos diferentes, um por IP (infra) e outro por `user_id` (produto)
- [x] Alocação de API key por usuário (`allocate_api_key`/`get_user_id_by_api_key`,
      `tools/redis/api_key.py`) — ligado via `POST /v1/keys` (`interfaces/api/routes/keys.py`, ver
      seção API acima)
- [ ] Cache de sessão: mover/duplicar o histórico curto de mensagens (hoje via `$slice: -5` no
      Mongo) para Redis, com TTL, reduzindo round-trip ao Mongo em cada turno
- [x] Cache de `perfil_usuario` (hoje lido do Mongo a cada invocação em `main.py:executar_fluxo_assessor`)

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

Saiu do esqueleto: `interfaces/api/main.py` registra `health_router`, `chats_router` e `keys_router`
de verdade, com autenticação por API key (`X-API-Key` via `interfaces/api/auth.py`) e rate limiting
por IP (`slowapi`, `interfaces/api/rate_limiting.py`). `main.py api` já sobe esse app via
`uvicorn.run("interfaces.api.main:app", ...)`.

- [x] Escolher framework — FastAPI
- [x] Esqueleto de pastas — virou `interfaces/api/{main,auth,gen_key,rate_limiting}.py` +
      `routes/{chats,health,keys}.py` + `schemas/{chat,key}.py` (não `app/` como o TODO antigo previa)
- [x] `auth.py` — `get_current_user` via `APIKeyHeader` + `tools/redis/api_key.py:get_user_id_by_api_key`
- [x] `routes/chats.py` — `POST /v1/chats` (cria chat) e `POST /v1/chats/{chat_id}/messages`
      chamando `chat.service.send_message(...)`
- [x] `routes/health.py` — `/health/live` e `/health/ready` (ping no Redis)
- [x] Rate limiting por IP nas rotas de chat (`slowapi`, 5/min criar chat, 10/min mensagem)
- [x] `gen_key.py:generate_api_key` ligado à API — `POST /v1/keys` (`interfaces/api/routes/keys.py`),
      corpo `{nome, email}`, resolve o usuário por email (`chat/service.py:obter_ou_criar_usuario`,
      novo — reaproveita se o email já existir, senão cria) e chama `allocate_api_key`; `409` se o
      usuário já tiver uma key ativa (não dá pra reexibir, só o hash fica salvo). Endpoint público,
      só com rate limit (5/min, mesmo padrão dos outros endpoints) — decisão consciente: emitir key
      sem auth prévia é aceitável no estágio atual do projeto, sem introduzir uma segunda credencial
      (admin key) só pra isso
- [x] Validar ownership do chat antes de `send_message` — `chat/service.py:obter_dono_chat` (novo)
      + `routes/chats.py:_validar_ownership`: `404` se o chat não existe, `403` se existe mas é de
      outro usuário. Só foi possível porque `create_chat` passou a persistir o documento no Mongo
      na hora da criação (`chat/repositories.py:criar_chat`) — antes `POST /v1/chats` só gerava um
      `uuid4()` em memória e não gravava nada, então não tinha contra o que validar ownership até a
      primeira mensagem ser enviada
- [ ] Endpoint de streaming (SSE ou WS) para respostas incrementais do LangGraph
- [x] Ligar `main.py api` ao app de `interfaces/api/main.py` — `run_api()` chama
      `uvicorn.run("interfaces.api.main:app", host="0.0.0.0", port=8000, reload=True)`
- [ ] Dockerfile + healthcheck (compose hoje só sobe a infra — postgres/mongo/redis/qdrant —, não a
      própria API)
- [x] `GET /v1/chats/{chat_id}/messages` (listar histórico) — `routes/chats.py:get_messages`, mesma
      checagem de ownership dos outros endpoints do recurso, mapeando `chat/models.py:Role`
      (`human`/`ai`) pro `Role` da API (`user`/`assistant`). **Achado:** `MessageResponse` tinha um
      campo `created_at` que nada no storage preenche — nem `chat/models.py:ChatMessage` nem
      `tools/mongo/chats/schemas.py:Mensagem` guardam timestamp por mensagem (só o chat como um
      todo tem `created_at`/`updated_at`). Removido o campo do schema em vez de inventar um
      timestamp que não existe nos dados
- [x] Tratamento de erro nas rotas de `routes/chats.py` — `create_chat`/`send_message` agora têm
      `try/except` com log (`config/logging.py:get_logger`) e retornam `500` com corpo padronizado
      do FastAPI (`{"detail": ...}` via `HTTPException`) em vez de traceback cru

## TUI com Textual — concluída (painel de agente ativo fica pendente)

Substituiu/complementa a interface atual (Rich + pyfiglet) por uma TUI de verdade com
[Textual](https://github.com/Textualize/textual). Estrutura espelha `interfaces/terminal/`
(`app.py` = lógica, `display.py` = apresentação), mais `app.tcss` pro styling (stylesheet externo
do Textual em vez de CSS como string Python).

- [x] Adicionar `textual` às dependências (`uv add textual`)
- [x] `interfaces/tui/app.py` — `AssessorTUI`, tela de chat (input fixo embaixo, histórico
      rolável), chamando `chat.service.send_message(...)` — nunca `graph/builder.py` direto
- [x] Widget de histórico com bolhas usuário/assistente — `interfaces/tui/display.py:Bubble`
      (classes CSS `usuario`/`assistente`/`pensando` em vez da lógica Rich de `exibir_usuario`/
      `exibir_assistente`, que não se aplica a widgets Textual)
- [x] Indicador de "pensando..." — `Bubble` com classe `pensando`, `_processar` roda
      `chat.service.send_message` num `@work(thread=True)` pra não travar a UI
- [ ] Tela/painel lateral opcional mostrando qual agente está ativo (`agentes_chamados` do
      estado) — adiado deliberadamente, fora do escopo da primeira versão
- [x] Comando `/exit` e `Ctrl+C` encerrando a sessão via `chat.service.encerrar_sessao`
- [x] Bootstrap de usuário/sessão extraído pra `chat/service.py:iniciar_sessao()` — antes
      duplicado em `interfaces/terminal/app.py`, agora reaproveitado por terminal e TUI

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

## LangSmith — observabilidade / auditoria dos agentes

Hoje não existe nenhuma instrumentação de tracing sobre o grafo — os únicos logs são os manuais via
`config/logging.py:get_logger`, sem visibilidade de latência, tokens ou prompt/resposta completos por
nó do LangGraph (guardrail, router, financeiro, agenda, faq, orquestrador). `langsmith` já é
dependência transitiva do `langchain` (pinned no `pyproject.toml`), só falta ligar.

- [ ] Variáveis `LANGCHAIN_TRACING_V2`, `LANGCHAIN_API_KEY`, `LANGCHAIN_PROJECT` em
      `config/settings.py` + `.env.example`
- [ ] Decidir escopo do projeto no LangSmith (um projeto por ambiente — dev/prod — ou um só)
- [ ] Confirmar que o trace não vaza dado sensível — checar se passa pelo guardrail de entrada
      (`agents/nodes/guardrail/entrada.py`) antes de ligar tracing em produção
- [ ] Tag/metadata por run (ex. `user_id`, nó ativo) pra permitir auditoria por usuário/sessão, não só
      por chamada de LLM solta

## Débitos técnicos / melhorias soltas

- [x] Transformar as tabelas de `types` em `enum` Python + tipo nativo do Postgres — `TransactionType`
      e `PaymentType` (`tools/postgres/models.py`) agora são `StrEnum` mapeados pra `SAEnum(...,
      create_type=False)` sobre os tipos `transaction_type`/`payment_type` já criados via migration
      (`..._transaction_type_and_payment_type_as_...py`); `resolve_type_id` virou
      `resolve_transaction_type`, puramente em Python (`tools/postgres/helpers.py`)
- [x] `ruff` (lint + format) adicionado e aplicado no repo (`dd09c43`, `c95365c`) — `ruff check .`
      hoje passa limpo (`All checks passed!`, só `BLE001` ignorado deliberadamente, ver comentário
      em `pyproject.toml`)
- [x] `[project.scripts]` no `pyproject.toml` — `assessor-ai = 'main:main'`
- [x] `interfaces/terminal/app.py` reaproveita usuário existente — `tools/mongo/users/core.py:buscar_algum`
      (novo, `collection.find_one()` sem filtro) exposto via `chat/repositories.py` e
      `chat/service.py:buscar_usuario_existente`. Terminal chama isso primeiro; só cria usuário
      mock novo (`generate_user` + `garantir_usuario`) se o Mongo ainda não tiver nenhum.
      **Simplificação deliberada:** `buscar_algum` pega "qualquer" usuário, sem filtro por
      identidade — ok porque o terminal é uma ferramenta pessoal de um usuário só (diferente da
      API, que já resolve `user_id` real via API key). Se o Mongo acumular mais de um usuário por
      outro motivo, isso passa a pegar um arbitrário — não é um problema hoje.
- [ ] Adicionar checagem de tipagem estática com **mypy** (ruff cobre lint/format mas não faz type
      checking; mypy é o que de fato valida as anotações de tipo) — avaliar `strict` vs. modo
      incremental dado que o projeto ainda não tem nenhuma tipagem checada
- [x] `config/settings.py` dessincronizado do `.env.example` — alinhado nos dois lados em torno do
      padrão `<SISTEMA>_URL` (`POSTGRES_URL`, `MONGO_URL`, `REDIS_URL`, `QDRANT_URL`); removido
      `MONGO_USER`/`MONGO_PASSWORD` (não usados, a URI já carrega credenciais); `QDRANT_CLUSTER_ENDPOINT`
      renomeado para `QDRANT_URL` (`tools/qdrant/connection.py` ajustado junto); `MONGO_COLLECTION_NAME`
      e `QDRANT_COLLECTION_NAME` (obrigatórios no `Settings`, faltavam no `.env.example`) documentados.
      README também tinha `DATABASE_URI`/`MONGODB_URI` (nomes de antes da migração pra Docker Compose)
      e um `interfaces/api/app.py` que não existe (é `main.py`) — corrigidos.
      **Atenção:** isso não toca `.env` local (gitignored) — se o seu `.env` ainda tiver os nomes
      antigos, precisa atualizar manualmente pra bater com o novo `.env.example`.

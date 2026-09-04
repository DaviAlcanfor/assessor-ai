# TODO

Próximos passos planejados. Contexto do projeto em [AGENTS.md](AGENTS.md).

## Refatoração: padrão limpo e injeção de dependência — a fazer

Regra transversal: classe é pra segurar dependência injetada. Classe sem estado com um método é
função de fantasia — não converter por estética.

- [~] **mypy + ruff estrito** — `mypy` está configurado (`[tool.mypy]` no pyproject, `files=["src"]`)
      e passa limpo: `Success: no issues found in 89 source files`. **Falta o job no CI** — `ci.yml`
      roda só `ruff check` e `pytest`. Original: nenhum type checker revisa o código hoje. Adicionar `mypy` ao dev
      group, um job no CI, e endurecer o ruff (hoje é quase default). Consertar o que aparecer
      (ex.: `Estado.mensagem_bloqueada: str` recebendo `None` em `graph/state.py`; retornos `-> dict`
      genéricos). Zero mudança de estrutura; é só instalar o crítico. **Faz isso primeiro.**
- [~] **Matar efeito colateral de import** — o grafo agora é compilado no `lifespan` da API, não
      mais na primeira mensagem. Mas as duas causas originais continuam de pé: `core/config.py`
      ainda muta `os.environ` no import e `graph/builder.py` ainda monta `grafo` no import com
      `_fluxo`/`_lock` global. Original: `config/settings.py` instancia `Settings()` e **muta
      `os.environ`** só de importar o módulo (linhas ~44-49); `graph/builder.py` monta `grafo` no
      import e tem `_fluxo`/`_lock` como global de módulo. Mover pra função chamada uma vez no
      startup (lifespan da API / bootstrap da TUI). Diff pequeno e isolado.
- [x] **`SecretStr` nos segredos** — feito, e mais amplo que o pedido: as URLs de conexão também
      viraram `SecretStr`, porque carregam usuário e senha embutidos. Original: `config/settings.py`: trocar `str` por `SecretStr` em
      `GEMINI_API_KEY`, `GROQ_API_KEY`, `POSTGRES_URL`, `MONGO_URL`, `QDRANT_API_KEY`,
      `SIGNUP_SECRET`. Evita vazamento acidental em log/traceback/`/docs`. **Não** embrulhar o que
      não é segredo (nomes de coleção, `A2A_BASE_URL`, `LANGSMITH_PROJECT`).
- [x] **Extrair redação de PII pra módulo neutro** — virou `core/privacy.py`. Original: `chat/repositories.py` importa
      `anonimizar_entrada` de `agents/nodes/guardrail/entrada.py`: a persistência reachando dentro
      da camada de agentes. Mover `anonimizar_entrada` (+ os padrões PII) pra um módulo neutro tipo
      `src/assessor_ai/privacy/` que persistência e guardrail importam. Remove a violação de camada.
- [~] **`repositories.py` → classes injetadas** — feito na camada de dados: `ChatsRepo`,
      `UsuariosRepo`, `FinanceiroRepo`, `AgendaRepo`, `FaqRepo`, cada um recebendo a conexão no
      `__init__` (o `monkeypatch` frágil dos testes morreu junto). `UserRepository`/`ProfileCache`
      saíram como `tools/usuarios/` e `core/cache.py`. Falta só `repositories/chat_repository.py`,
      que hoje é fachada fina de funções sobre esses repos. Original: hoje é um módulo de ~15 funções que fala com
      Mongo + Postgres + Redis ao mesmo tempo (são 3 repositórios colados). Quebrar em
      `ChatRepository` / `UserRepository` (talvez `ProfileCache` pro Redis), cada uma recebendo seu
      client no `__init__`. Um de cada vez. Destrava teste com fake e mata o `monkeypatch` frágil.
- [ ] **`services/chat_service.py` → classe** — `ChatService(chat_repo, user_repo, graph,
      rate_limiter)` em vez de funções soltas importando o repositório. Depende do item acima. Os
      testes em `tests/services/test_chat_service.py` passam a injetar fakes em vez de
      `monkeypatch.setattr` em string.
- [x] **Não reduzir número de arquivo** — respeitado: a divisão virou `services/` +
      `repositories/` + `schemas/` (mais separação, não menos). Original: `models`/`repositories`/
      `runner`/`service` é uma divisão sã. A pasta precisa de *mais* separação (itens acima), não
      menos. Confusão ≠ contagem de arquivo.
- [ ] **Nodes → classe só se ganharem dependência injetada** — hoje são `async def(estado) -> dict`
      puxando colaborador de global (`llm_guardrail`, `financeiro_app`). Se o LLM/tools/clock
      passarem a ser injetados, a classe vira o container natural (é o que o outro projeto faz:
      node = classe que segura `agent_factory`, `clock`, `tools`). Node genuinamente sem estado
      continua função. Decidir **depois** dos itens de DI — vai estar claro.
- [ ] **Graph → função que retorna, não módulo com global** — o smell real é `grafo`/`_fluxo`/`_lock`
      no topo de `builder.py`, não "falta ser classe". `build_graph(deps) -> CompiledGraph` chamada
      uma vez no startup basta. Vira classe (`AgentGraph` como porta) só se adotar DI a sério.
- [~] **API robusta** — taxonomia de exceção + exception handler saiu (`services/exceptions.py` +
      `api/exception_handlers.py`). Faltam: validar `chat_id` como UUID na fronteira, logging
      estruturado com request id, e o bypass gritar no log no startup. Original: independente do resto, pode ser a qualquer momento:
      taxonomia de exceção + um exception handler, no lugar de `except Exception` em toda rota;
      validar `chat_id` como UUID na fronteira (422 pra lixo); logging estruturado com request id;
      o bypass `API_KEY_AUTH_ENABLED=false` que injeta usuário aleatório precisa **gritar no log no
      startup** (arma apontada pro pé se subir em prod).

Referências pra estudar o padrão: livro **"Architecture Patterns with Python"** (grátis em
cosmicpython.com — ports/adapters, repository, service layer, DI), canal **ArjanCodes**, fonte da
org **encode** no GitHub (FastAPI/Starlette/httpx).

## `tools/` por feature, com um `*Repo` por domínio — concluída

Antes: uma pasta por banco (`postgres/`, `mongo/`, `redis/`, `qdrant/`), tools como funções soltas de
módulo. Depois: uma pasta por feature, um `*Repo` por feature, conexões em `tools/infra/`.

| antes | depois |
|---|---|
| `postgres/financeiro/core.py` (5 funções `@tool`) | `financeiro/repo.py:FinanceiroRepo` |
| `postgres/agenda/core.py` (4 funções `@tool`) | `agenda/repo.py:AgendaRepo` |
| `qdrant/faq/core.py` | `faq/repo.py:FaqRepo` |
| `mongo/chats/core.py` + `mongo/helpers.py` | `chats/repo.py:ChatsRepo` |
| `mongo/users/` + `postgres/users/` + `redis/api_key.py` | `usuarios/repo.py:UsuariosRepo` |
| `postgres/models.py` (todos os models juntos) | `financeiro/models.py`, `agenda/models.py`, `usuarios/models.py` |
| `*/connection.py` (4 arquivos, funções + globais) | `infra/{postgres,mongo,redis,qdrant}.py` (uma classe cada) |
| `postgres/helpers.py` | datas → `infra/postgres.py`; `resolve_transaction_type` → `financeiro/repo.py` |

O que morreu de repetição: 10 `with get_session()`, 10 `try/except → Response.error`, e a
serialização linha→dict duplicada (4 cópias → 1 `_serializar` por feature). Tudo isso virou
`@transacional` em `infra/postgres.py`.

Duas pegadinhas de LangChain verificadas na mão antes de escrever o código, ambas do mesmo tipo
(parâmetro interno vazando pro JSON schema que vai pro LLM):

- `@tool` num método deixa `self` no schema (`['self', 'a', 'b']`). Por isso o bind é
  `StructuredTool.from_function(repo.metodo)` dentro de `as_tools()`, com a instância já ligada.
- `functools.wraps` no `@transacional` deixa `s` (a sessão) no schema, porque `inspect.signature`
  segue `__wrapped__`. O decorator reescreve `__signature__` — corrige para toda tool, inclusive as
  que não passam `args_schema` (`total_balance`, `query_daily_events`).

Conferido que os 10 tools expõem exatamente os mesmos parâmetros de antes, sem `self` nem `s`.

- [x] `infra/` com `PostgresConn`, `MongoConn`, `RedisConn`, `QdrantConn` — todas lazy. O
      `GoogleGenerativeAIEmbeddings` do FAQ saiu de dentro da tool (era reconstruído a cada
      pergunta) e virou property da conexão
- [x] `mongo/connection.py` conectava no import (`banco = _conectar()`), violando o "nenhum I/O no
      import" do CODE_STYLE — a classe lazy corrige
- [x] Testes: `ConnFake` injetado no construtor no lugar do monkeypatch de `get_session`; os testes
      chamam `repo.metodo(...)` em vez de `tool.func(...)`
- [x] **Alembic**: `env.py` importava um caminho morto (`assessor_ai.config.settings`) e passava
      `POSTGRES_URL` como `SecretStr` pro `set_main_option` — as migrations estavam quebradas desde
      o refactor anterior. Agora importa os três módulos de models (senão o autogenerate dropa as
      tabelas que sumiram do metadata) e `alembic check` diz "No new upgrade operations detected"
- [x] **Mina desarmada no `env.py`**: as tabelas `checkpoint*` são criadas pelo `setup()` do
      LangGraph, não pelo Alembic. Sem `include_object` elas ficavam fora do `target_metadata` e um
      `--autogenerate` gerava um DROP delas — apagando o histórico de conversa de todos os usuários.
      Era pré-existente (o `env.py` nunca teve o filtro), apareceu ao rodar `alembic check`
- [ ] **Isolamento por usuário continua explícito em cada query** (`user_id == self.usuario`). Não
      inventei filtro implícito no ORM: o fix estrutural pra "esqueci o WHERE" é RLS no Postgres,
      não esperteza na camada de aplicação. Amarrado ao item de IDOR da seção Segurança

## Estrutura por camada no fluxo de chat — concluída

`chat/` e `interfaces/` foram dissolvidos: o fluxo de chat agora é `api/` → `services/` →
`repositories/`, com `schemas/` guardando os contratos. `tui/` e `a2a/` subiram um nível.
`core/`, `graph/`, `agents/` e `tools/` não mudaram — as tools continuam *package by feature*
(a razão de as duas réguas coexistirem está no CODE_STYLE.md).

| antes | depois |
|---|---|
| `interfaces/api/main.py` | `api/app.py` + `api/lifespan.py` (o lifespan saiu do corpo da app) |
| `interfaces/api/errors.py` | `api/exception_handlers.py` |
| `interfaces/api/{auth,gen_key}.py`, `routes/` | `api/` |
| `interfaces/api/schemas/` | `schemas/` |
| `chat/service.py` | `services/chat_service.py` |
| `chat/runner.py` | `services/runner.py` |
| `chat/exceptions.py` | `services/exceptions.py` |
| `chat/repositories.py` | `repositories/chat_repository.py` |
| `chat/models.py` | `schemas/models.py` |
| `interfaces/{tui,a2a}/` | `tui/`, `a2a/` |

- [x] Imports reescritos em `src/` e `tests/`; `pyproject.toml` (`entrypoint`) e `main.py`
      (alvo do uvicorn) apontando pra `assessor_ai.api.app:app`
- [x] Testes espelharam a mudança: `tests/api/`, `tests/services/test_chat_service.py`
- [x] README (árvore inteira), AGENTS.md e CODE_STYLE.md atualizados
- [ ] `repositories/` tem só `chat_repository.py`. Se aparecer um segundo repositório com domínio
      próprio, vale reavaliar se ele não deveria ser `repositories/<domínio>.py` em vez de um
      arquivo gordo

## Refatoração `config/` → `core/` + erros de domínio na API — concluída

A movimentação de `config/` e `interfaces/` pra dentro de `src/assessor_ai/` tinha ficado pela
metade: os arquivos novos existiam (`core/config.py`, `core/logging.py`, `core/privacy.py`,
`core/prompts/`, `core/cache.py`, `core/limiter.py`, `core/middleware.py`, `core/models.py`), mas
~40 módulos ainda importavam dos caminhos velhos — o pacote não importava, `just api` não subia e
o pytest não coletava. Fechado:

- [x] Imports atualizados em `src/` e `tests/` (`config.settings`→`core.config`,
      `config.logging`/`config.decorators`→`core.logging`, `agents.prompts`→`core.prompts`,
      `interfaces.api.rate_limiting` e `tools.redis.chat`→`core.limiter`,
      `tools.redis.perfil`→`core.cache`, `config.models`→`core.models`)
- [x] PII deduplicada: as regex viviam em `agents/nodes/guardrail/schemas.py` **e** em
      `core/privacy.py`. Ficou só a de `core/`; `chat/` e `core/logging.py` não importam mais de
      `agents/nodes/`
- [x] `REDIS_TOOLS` (em `tools/__init__.py`) removida — nenhum agente usava, e os dois consumidores
      importam direto do módulo
- [x] Testes que seguiram os módulos: `tests/core/{test_limiter,test_cache,test_logging}.py`
- [x] **Grafo compilado no `lifespan`**, não na primeira mensagem — `setup()` do checkpointer cria
      tabelas no Postgres, e o processo agora falha ao subir (em vez de aceitar tráfego e errar
      502 por mensagem) se o banco estiver fora
- [x] **Erros de domínio** em `chat/exceptions.py` + tradução pra HTTP em `interfaces/api/errors.py`
      (404/403/429/502 + handler de `Exception` que loga o traceback e devolve
      `ErrorResponse{detail, code}` genérico). `routes/chats.py` perdeu os `try/except`; ownership
      virou `chat_service.validar_ownership`
- [x] **`SecretStr`** em toda credencial de `core/config.py`, incluindo as URLs de conexão
- [x] **`WindowsSelectorEventLoopPolicy` em `main.py`** — psycopg3 async recusa o
      ProactorEventLoop (padrão do asyncio no Windows), então o pool do checkpointer nunca abria e
      todo turno morria num `PoolTimeout` de 30s em dev local. Só afeta Windows

Pendências que ficaram fora, de propósito:

- [ ] **Falha de upstream (Mongo/Postgres fora) devolve 500 genérico, não 503.** Só `send_message`
      converte falha em erro de domínio (`FalhaNoAgente` → 502); as outras rotas caem no handler
      de `Exception`. Mapear pra 503 exige embrulhar ~10 funções de `chat/repositories.py` — só
      vale se o front precisar distinguir "instável, tente de novo" de "quebrado"
- [ ] **Código morto pra apagar** (nada mais importa, tudo verificado): as 19 sobras de
      `tools/{postgres,mongo,redis,qdrant}/`, mais as pastas vazias `src/assessor_ai/config/`,
      `src/assessor_ai/interfaces/`, `src/assessor_ai/chat/`, `tests/interfaces/`, `tests/chat/`,
      `tests/tools/{postgres,redis}/`. Não removi por conta própria — deletar arquivo precisa de OK
      explícito, ver AGENTS.md
- [ ] **E2E real da API não rodou nesta máquina**: o Atlas recusa o handshake TLS daqui
      (`TLSV1_ALERT_INTERNAL_ERROR` nos três nós do shard — pinta como allowlist de IP, o mesmo
      diagnóstico que já está em `.agents/skills/mongo.md`). Verificado o que dava: `lifespan`
      compila grafo + checkpointer contra o Postgres real, e os 172 testes passam

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

Split em `tools/redis/{connection.py,api_key.py,chat.py,perfil.py,schemas.py}` feito, seguindo o
mesmo corte de `tools/postgres` e `tools/mongo`.

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
- [x] Cache de `perfil_usuario` — `tools/redis/perfil.py` (`buscar_perfil_cache`/`salvar_perfil_cache`/
      `invalidar_perfil_cache`, TTL de 1h) chamado em `chat/repositories.py:buscar_perfil`, que só
      cai no Mongo em cache miss. Cache invalidado em `encerrar_sessao` (`/exit`), quando o perfil
      pode ter sido atualizado a partir do resumo da sessão

## Qdrant — FAQ migrado de FAISS

RAG do FAQ agora roda sobre Qdrant (`tools/qdrant/faq/`), substituindo o FAISS local.

- [x] `tools/qdrant/faq/connection.py` — client lazy (`get_qdrant_client`), mesmo padrão sync
      lazy-singleton de `tools/postgres/connection.py`/`tools/mongo/connection.py` (o `connection.py`
      assíncrono citado antes aqui foi substituído por esse, mais simples e consistente com o resto
      do repo)
- [x] Variáveis `QDRANT_URL` / `QDRANT_API_KEY` no `.env.example`
- [x] `tools/qdrant/faq/core.py` — `faq_retriever` reimplementado sobre Qdrant: `@tool` +
      `@log_tool`, `args_schema=FaqRetrieverArgs`, retorna `Response.ok(results=[...])`, collection
      lida de `settings.QDRANT_COLLECTION_NAME` (antes hardcoded). `tools/faq_tools.py` (FAISS)
      removido; `tools/__init__.py` aponta pro novo módulo
- [x] Script de ingestão dos PDFs de `data/documents/` para a collection do Qdrant —
      `tools/qdrant/faq/ingest.py` (`python -m assessor_ai.tools.qdrant.faq.ingest`), separado do
      módulo da tool (que só faz busca)
- [ ] Decidir: Qdrant local (Docker, mesmo padrão do `docker-compose.yml`) vs. Qdrant Cloud — hoje
      o compose já sobe `qdrant/qdrant:latest` local
- [ ] Futuramente: collections separadas para `financeiro`/`agenda` (busca semântica sobre
      histórico), fora do escopo desta migração

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
- [x] `routes/health.py` — `/health/live` e `/health/ready` (ping no Redis e no Mongo — adicionado
      depois de um deploy real falhar por indisponibilidade do Mongo Atlas sem o readiness pegar,
      ver achado na seção Segurança abaixo)
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

## CD — deploy automático (FastAPI Cloud) — avaliado, ainda manual

Hoje `just deploy` roda `fastapi deploy` (fastapi-cloud-cli) na mão, depois do merge. CI
(`.github/workflows/ci.yml`) já roda lint+testes em todo push/PR pra `main`, então encadear um job
de deploy depois do `test` passar é tecnicamente simples — mas dois pontos em aberto antes de
automatizar:

- [ ] Confirmar na doc do FastAPI Cloud se `fastapi deploy` aceita um token não-interativo (secret
      do GitHub Actions) — o fluxo local hoje é `fastapi login` interativo; sem um modo não-interativo
      documentado, não dá pra rodar em CI
- [ ] Decidir se o deploy dispara direto após merge em `main` ou atrás de um gate manual (ex.:
      GitHub Environment com required reviewer) — os dois incidentes de produção já registrados na
      seção Segurança (TLS do Mongo Atlas, IP allowlist do Atlas) não teriam sido pegos pelo CI atual
      (só lint + testes sem I/O real), então merge verde não é garantia de deploy seguro hoje
- [ ] Se aprovado, um job novo em `ci.yml` (ou `cd.yml` separado), rodando só em push pra `main`
      (não em PR), depois do `test` passar

**Achado:** `.fastapicloudignore` mostra que o build da FastAPI Cloud lê `pyproject.toml`/`uv.lock`
direto (ignora `.venv`, `justfile`, etc.) — não depende de Dockerfile. O item pendente "Dockerfile +
healthcheck" na seção API acima é só sobre paridade do `docker-compose` local (subir a própria API
junto da infra), não bloqueia esse deploy automático.

## TUI com Textual — concluída (painel de agente ativo fica pendente)

Substituiu/complementa a interface atual (Rich + pyfiglet) por uma TUI de verdade com
[Textual](https://github.com/Textualize/textual). Estrutura espelha `interfaces/terminal/`
(`app.py` = lógica, `display.py` = apresentação), mais `app.tcss` pro styling (stylesheet externo
do Textual em vez de CSS como string Python).

- [x] Adicionar `textual` às dependências (`uv add textual`)
- [x] `interfaces/tui/app.py` — `AssessorTUI`, tela de chat (input fixo embaixo, histórico
      rolável), chamando `chat.service.send_message(...)` — nunca `graph/builder.py` direto
- [x] Widget de histórico com bolhas usuário/assistente — `interfaces/tui/display.py:Bubble`
      renderiza o mesmo `rich.panel.Panel` de `interfaces/terminal/display.py` (título "Você"/
      "Assessor" embutido na borda, verde/cyan), em vez de reinventar o visual só com CSS do
      Textual. `MessageRow` (novo, `Horizontal`) alinha a bolha à direita (usuário) ou esquerda
      (assistente) via `align-horizontal`, mantendo a coluna do chat centralizada
- [x] Indicador de "pensando..." — `Pensando` (novo, `Horizontal` com `LoadingIndicator` nativo do
      Textual, spinner animado) substitui o texto estático; `_processar` roda
      `chat.service.send_message` num `@work(thread=True)` pra não travar a UI
- [x] Arte ASCII (pyfiglet, mesma fonte `doom` do terminal) no topo da TUI, cyan
- [x] Layout responsivo — `#historico`/`Input`/`#logs`/`#banner` usam `width: 90%; max-width: 120`
      em vez de largura fixa em células; testado em 80/120/180 colunas, sempre centralizado
      (`Screen { align: center top }`). **Achado:** o `align` do Textual centraliza a *pilha* de
      filhos pela largura do mais largo entre eles, não cada um individualmente — o banner (largura
      fixa, menor que os outros) colava na borda esquerda em vez de centralizar sozinho até trocar
      `width: auto` por `width: 90%` + `content-align: center middle` nele também
- [x] Painel de logs (`RichLog`, `#logs`) abaixo do input, fora da área de scroll do chat —
      `AssessorTUI._redirecionar_logs()` limpa os `StreamHandler`s (stderr) que `config/logging.py:
      get_logger` anexa por módulo e centraliza tudo num handler único escrevendo no widget (stderr
      cru durante a tela alternativa do Textual corrompia a UI)
- [ ] Tela/painel lateral opcional mostrando qual agente está ativo (`agentes_chamados` do
      estado) — adiado deliberadamente, fora do escopo da primeira versão. **Único item
      funcionalmente pendente da TUI** neste momento
- [ ] Avaliar `textual-serve` pra servir a TUI atual (`tui/app.py`) no navegador em vez
      de um frontend React/JS — reaproveita `Bubble`/`MessageRow`/`Pensando` sem código novo de
      frontend; trade-off é ficar preso à estética/interação de terminal (sem componentes HTML
      ricos, layout mobile limitado). Suficiente pro estágio pessoal do projeto; revisitar se um dia
      precisar de UX além de TUI
- [x] Comando `/exit` e `Ctrl+C` encerrando a sessão via `chat.service.encerrar_sessao`
- [x] Bootstrap de usuário/sessão extraído pra `chat/service.py:iniciar_sessao()` — antes
      duplicado em `interfaces/terminal/app.py`, agora reaproveitado por terminal e TUI

## Testes — suíte iniciada, só funções puras por enquanto

Pasta `tests/` criada espelhando a estrutura de `tools/` (package by feature, mesmo corte usado no
resto do repo). `chat/` e `agents/nodes/{guardrail,router}` já têm teste; `tools/qdrant`, `tools/mongo`
e o resto de `agents/nodes`/`graph` ainda não (ver bullets abaixo).

- [x] `pytest` como dev dependency (`uv add --dev pytest`, ficou `pytest>=9.1.1`) — `pytest-mock`/
      `pytest-asyncio` adiados até surgir necessidade real (nada async ou precisando de mock pesado
      nos testes de hoje)
- [x] `tests/tools/` — os três módulos sem I/O que o TODO já apontava como ponto de partida:
      `test_response.py` (`Response.ok`/`Response.error`), `postgres/test_helpers.py`
      (`resolve_transaction_type` com todos os aliases PT-BR, e `local_date`/`local_date_filter`/
      `local_date_range_filter` — testados compilando a expressão SQLAlchemy pra string via
      `.compile(compile_kwargs={"literal_binds": True})`, sem precisar de banco real),
      `redis/test_schemas.py` (`_hash_api_key`, `_chave_mensagem`, `_chave_api_key`,
      `_chave_api_key_lookup`, `_chave_perfil`). 29 testes, todos passando (`just test` ou
      `pytest`, roda em ~3s). `get_category_id` (`tools/postgres/helpers.py`) ficou de fora — precisa
      de uma `Session` de verdade (ou SQLite in-memory), é teste de integração, não unitário puro
- [x] Comando `just test` no `justfile`
- [ ] `tests/conftest.py` com fixtures compartilhadas — provavelmente mocks de
      `tools/postgres/connection.py:get_session` e `tools/mongo/connection.py` pra não depender de
      banco real nos testes unitários
- [x] `tests/chat/` — `chat/service.py` e `chat/runner.py` com o grafo mockado (`monkeypatch` no
      `fluxo_agentes`/`repositories`/`runner.executar`, mesmo padrão de
      `tests/agents/nodes/guardrail/test_entrada.py`, sem chamar LLM real). Cobre: extração da
      última `AIMessage`, propagação de `thread_id`/`tags`/`metadata` pro `invoke()`, isolamento do
      `current_user_id()` (setado durante o `invoke`, restaurado depois), bloqueio por
      `LimiteDeMensagensExcedido`, redação de PII antes de persistir e o caminho "sem resposta" não
      persistindo mensagem. 7 testes novos, 110/110 no total
- [ ] Decidir separação `tests/unit/` vs. `tests/integration/` (integration = sobe Postgres/Mongo
      via infra real de Postgres/Mongo) antes de crescer demais, ou manter achatado enquanto a suíte
      for pequena. **Achado:** o `config/docker.py` que subia essa infra localmente foi removido no
      commit `16479fa` — não existe mais no repo (nem em `CLAUDE.md`, que ainda instrui "não rodar
      `docker stop`/`start` fora do fluxo de `config/docker.py`"); confirmar com o usuário como a
      infra local sobe hoje antes de escrever testes de integração, e atualizar essa instrução em
      `CLAUDE.md`
- [ ] `tests/tools/qdrant/` — `faq_retriever` (`tools/qdrant/faq/core.py`) sem nenhum teste hoje.
      Precisa mockar o client do Qdrant (`query_points`) e `GoogleGenerativeAIEmbeddings.embed_query`
      via `monkeypatch`, mesmo padrão de fake usado em `tests/tools/redis/fakes.py` (não bate
      diretamente porque aqui as duas dependências são clientes externos, não um `Redis` só)
- [ ] Outros módulos ainda sem teste nenhum: `tools/mongo/` (chats, users), `tools/postgres/agenda/
      core.py` e `financeiro/core.py` (só `helpers.py` tem teste), e os nós do grafo além de
      guardrail/router (`agents/nodes/{agenda,faq,financeiro,orquestrador}.py`, `graph/builder.py`) —
      avaliar prioridade quando a suíte crescer, não é urgente pro estágio atual
- [x] CI (GitHub Actions) — `.github/workflows/ci.yml`, roda em push pra `main` e em PR: `uv sync
      --locked` → `ruff check .` → `pytest`. **Achado:** `assessor_ai/__init__.py` importa
      `graph/builder.py`, que puxa a cadeia inteira até `config/settings.py:Settings()` — ou seja,
      até um teste de função pura (`tools/response.py`, sem nenhum import próprio) dispara a
      validação de *todas* as env vars obrigatórias só por importar qualquer coisa de dentro de
      `assessor_ai`. Sem `.env` (caso do CI, que não tem o arquivo — é gitignored), a coleta dos
      testes quebra com `ValidationError`. Resolvido com valores dummy direto no `env:` do job
      (não precisa de secret nenhum, já que os testes de hoje não fazem I/O real) — mas é sinal de
      acoplamento a revisar se a suíte crescer pra módulos que hoje não tocam `Settings`
- [x] Corrigido de passagem: `interfaces/tui/app.py:BINDINGS` sem `ClassVar` (RUF012) — única
      pendência do `ruff check .` no repo; corrigido antes de ligar o CI pra não nascer vermelho

## LangSmith — observabilidade / auditoria dos agentes

Hoje não existe nenhuma instrumentação de tracing sobre o grafo — os únicos logs são os manuais via
`config/logging.py:get_logger`, sem visibilidade de latência, tokens ou prompt/resposta completos por
nó do LangGraph (guardrail, router, financeiro, agenda, faq, orquestrador). `langsmith` já é
dependência transitiva do `langchain` (pinned no `pyproject.toml`), só falta ligar.

- [x] Variáveis em `config/settings.py` + `.env.example` — usados os nomes atuais do SDK
      (`LANGSMITH_TRACING`/`LANGSMITH_API_KEY`/`LANGSMITH_PROJECT`; `LANGCHAIN_*` do LangChain
      antigo virou alias legado dentro do próprio `langsmith` client)
- [x] Propagate pro `os.environ` — `config/settings.py`, logo após `settings = Settings()`: se
      `LANGSMITH_TRACING` estiver true, exporta as 3 vars pro `os.environ` do processo. Necessário
      porque o SDK do LangSmith lê `os.environ` direto (dentro do `langchain-core`), e
      `pydantic-settings` só popula o objeto `Settings` — sem isso, tracing não ativava rodando
      `python main.py terminal` puro (sem `infisical run --`, que já injeta no processo por conta
      própria). Verificado ponta a ponta: mensagem de teste no terminal gerou 10 runs no projeto
      `assessor-ai` (LangGraph root, cada nó, cada LLM call), confirmado via `POST
      /api/v1/runs/query` da API do LangSmith
- [x] Tag/metadata por run (`user_id`, `session_id`) — `chat/runner.py:executar` passa
      `config={"tags": ["chat"], "metadata": {"user_id": ..., "session_id": ...}}` pro
      `fluxo_agentes.invoke(...)`. Propaga automaticamente pra todo run filho (nós do grafo, LLM
      calls) — confirmado via API, `user_id`/`session_id` aparecem em todos os spans do turno.
      **Achado:** a primeira tentativa foi embrulhar `chat/service.py:send_message` inteiro num
      `@traceable` — quebrou com `TracerException('No indexed run ID ...')` em toda chamada de LLM,
      porque `send_message` chama `runner.executar` → `fluxo_agentes.invoke(...)`, que já tem tracer
      próprio auto-anexado pelo LangGraph; os dois mecanismos (`@traceable` manual +
      auto-instrumentação via env var) colidem quando aninhados. Resolvido passando tags/metadata
      direto no `config` do `invoke()` (mecanismo nativo do LangChain) em vez de decorator por fora
- [x] `@traceable` nos pontos de I/O que o LangChain não rastreia sozinho — `chat/repositories.py`
      (`buscar_perfil`, `buscar_historico`, `salvar_mensagens`, `run_type="tool"`), dando visibilidade
      de latência Mongo/Redis separada da latência do LLM (sem isso só aparecia o `graph.invoke()`
      isolado). Aparecem como runs raiz próprios (não aninhados sob o turno do chat), já que não dá
      pra embrulhar `send_message` sem reintroduzir o bug acima — trade-off aceito
- [x] Redação de dado sensível nos pontos acima — `process_outputs`/`process_inputs` em
      `buscar_perfil`/`buscar_historico`/`salvar_mensagens` reaproveitam
      `agents/nodes/guardrail/entrada.py:anonimizar_entrada` (mesmo regex de PII do guardrail) antes
      de mandar pro LangSmith Cloud
- [ ] **Gap que ainda falta:** a redação acima cobre só os pontos com `@traceable` manual. O
      `LangGraph chain` raiz e o `guardrail_entrada_node` em si (auto-rastreados pelo LangChain) ainda
      logam a mensagem **crua** do usuário como input — a anonimização só existe no *output* do nó de
      guardrail (`no_guardrail_entrada`, que substitui a mensagem no estado por
      `texto_anonimizado`), não afeta o que o LangChain já capturou como input do run antes disso.
      Resolver de verdade exige um `anonymizer=`/`hide_inputs=` no `Client` global do LangSmith que o
      LangChain usa pra auto-tracing (não dá pra fazer só com `@traceable` local) — falta decidir se
      vale a complexidade nesse estágio do projeto ou se basta não rodar tracing em produção com dado
      real sem isso
- [ ] Decidir escopo do projeto no LangSmith (um projeto por ambiente — dev/prod — ou um só)

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

## Segurança — achados pendentes

Lista de achados de uma revisão de segurança, triados por prioridade (risco de vazamento/alteração
de dado entre usuários primeiro, robustez/infra por último) após o 500 em produção no `POST
/v1/keys` (Mongo Atlas com TLS handshake incompatível no Python 3.14 — resolvido travando
`requires-python` no `pyproject.toml`).

- [x] Race condition na criação de API key (`allocate_api_key`) — `exists()` + `pipeline.set()` não
      era atômico (duas requests simultâneas furavam o "1 key por usuário"); trocado por `SET ... NX`
      do Redis, atômico de verdade (`tools/redis/api_key.py`)
- [x] `POST /v1/keys` é público e cria usuário/key só com nome + email — adicionado gate por secret
      compartilhado (`X-Signup-Secret`, `SIGNUP_SECRET` no `Settings`, `interfaces/api/auth.py:
      verify_signup_secret`, comparação com `secrets.compare_digest`). Precisa configurar
      `SIGNUP_SECRET` no painel do FastAPI Cloud antes do próximo deploy, senão o endpoint quebra
      (`Settings()` exige a var)
- [x] Ownership não é protegido na camada de persistência (só nas rotas) — `GET
      /v1/chats/{id}/messages` era o caminho mais sensível (lê histórico inteiro); `user_id` agora
      passa até o filtro do Mongo (`chat/service.py:get_history` → `chat/repositories.py:
      buscar_historico` → `tools/mongo/chats/core.py:buscar`), então mesmo que uma rota futura
      esqueça `_validar_ownership`, a query não devolve chat de outro usuário. `buscar_dono_chat` e
      `salvar_mensagens` continuam só por `session_id` de propósito (são os pontos que decidem
      ownership/criam o documento, não podem filtrar por um `user_id` ainda não confirmado)
- [x] SQL injection via `ILIKE` — **verificado, falso positivo.** Todos os usos (`financeiro/core.py`,
      `agenda/core.py`) são `Column.ilike(f"%{texto}%")` via SQLAlchemy ORM, que sempre bind-parametriza
      o argumento (nunca concatena na string SQL). Não tem `text()` nem SQL cru com f-string em
      lugar nenhum. Sem ação necessária
- [x] Exposição de secrets (revisar logs, configs, respostas de erro) — **verificado, já mitigado.**
      `.env` nunca foi commitado (conferido via `git log --all -- .env`, vazio); `FastAPI()` roda sem
      `debug=True`, então exceptions não tratadas caem no handler padrão (`Internal Server Error`
      genérico, sem stack trace pro cliente — confirmado no 500 real do `POST /v1/keys`);
      `routes/chats.py` já captura e retorna mensagem própria em vez de `str(e)`. Fica só o gap de PII
      nos logs de tool (`log_tool`, item abaixo), que é sobre dado sensível, não credencial
- [x] `asynccontextmanager` pro lifespan do banco (Postgres) — `tools/postgres/connection.py:
      dispose_engine()` (novo) descarta o pool de conexões; `interfaces/api/main.py` chama no
      `lifespan` do FastAPI, no shutdown. Engine continua lazy (recriado sob demanda no próximo
      `get_session()`), só ganhou um jeito explícito de fechar em vez de depender do GC
- [x] Vazamento de PII: trocar `MemorySaver` por `MongoDBSaver` como checkpointer do LangGraph
      (`graph/builder.py`) — estado do grafo agora sobrevive a restart, em vez de morrer em memória.
      **Achado:** `langgraph-checkpoint-mongodb` não tem mais uma classe `AsyncMongoDBSaver`
      separada (o nome do TODO era de uma versão antiga da lib) — a `MongoDBSaver` atual (0.4.0) já
      implementa os métodos síncronos (`get_tuple`/`put`, usados por `.invoke()`) e assíncronos
      (`aget_tuple`/`aput`) na mesma classe; como todo o resto da stack (`chat/runner.py`,
      `chat/service.py`, rotas da API) é síncrono hoje, ficou no lado síncrono — trocar pra
      `.ainvoke()` de verdade é reescrita maior, fora do escopo daqui. **Achado 2:** a versão
      estável da lib trava `pymongo<4.17`, incompatível com o `pymongo>=4.17.0` pinado no
      `pyproject.toml` — relaxado para `>=4.12,<4.17` (`pymongo==4.16.0` instalado); o pin em
      `>=4.17.0` não tinha relação com o bug de TLS handshake do Mongo Atlas mencionado na seção de
      Segurança abaixo (esse já foi resolvido travando `requires-python<3.14`). Verificado
      ponta a ponta: grafo de teste com o `checkpointer` real gravou e recuperou estado via Mongo
      (`graph_checkpoints`/`graph_checkpoint_writes`, nomeadas à parte pra não colidir com os
      defaults da lib), suíte completa (103 testes) e `ruff check` seguem passando
- [x] Guardrail de entrada logando a mensagem original (não a anonimizada) em algum ponto do erro —
      `no_guardrail_entrada` (`agents/nodes/guardrail/entrada.py`) já rodava `anonimizar_entrada`
      antes de checar bloqueio, mas o `logger.warning` no caminho de bloqueio usava
      `ultima_msg.content` (cru) em vez de `texto_anonimizado`. Único ponto do módulo com esse
      padrão (conferido: `saida.py` não loga conteúdo de mensagem). Trocado para logar o texto já
      anonimizado.
- [x] Decorator de logging de tool (`log_tool`) registrando o resultado completo da tool, sem redação
      — `config/decorators.py:log_tool` reaproveita `anonimizar_entrada` (mesmo regex de PII do
      guardrail, já usado em `chat/repositories.py` pra redigir antes do LangSmith) sobre
      `args`/`kwargs`/`result` antes de logar. Import de `assessor_ai.agents.nodes.guardrail.entrada`
      feito dentro da função (lazy) pra não puxar `graph/llm.py` (client LLM) na hora que
      `config/decorators.py` é importado, que é cedo (postgres tools). Teste novo:
      `tests/test_decorators.py`
- [x] Guardrail de entrada falha aberto: usa só regex, então input não capturado pelo regex passa como
      aprovado — precisa de mecanismo mais robusto (não só regex). O bypass real: `_detectar_injecao`/
      `_detectar_acesso_interno` (regex) bloqueiam ANTES do classificador LLM, mas quem passa por eles
      caía direto no LLM que só classificava OFENSIVO/PERIGOSO/ILICITO/POLITICO/INDICACAO_INVEST —
      nunca tentativa de injeção/exfiltração fora do regex. Corrigido reaproveitando o mesmo classificador
      LLM (`GuardrailPrompts.CLASSIFICADOR`) em vez de adicionar uma segunda chamada: duas categorias
      novas (`INJECAO_PROMPT`, `ACESSO_INTERNO`, `agents/nodes/guardrail/schemas.py`) descritas no
      prompt e mapeadas em `_RESPOSTAS_BLOQUEIO` com o mesmo motivo/mensagem do bloqueio regex. Regex
      continua como camada barata que bloqueia sem custo de LLM; agora o que escapa dela ainda é pego
      semanticamente. Teste novo cobrindo o bypass real (frase fora do regex, LLM mockado retornando
      `INJECAO_PROMPT`): `tests/agents/nodes/guardrail/test_entrada.py`
- [x] Datas financeiras usando timezone errado — `daily_balance` e `query_transactions`
      (`tools/postgres/financeiro/core.py`) filtravam com `func.date(Transaction.occurred_at)` cru
      (converte pro fuso da sessão do Postgres/UTC, não America/Sao_Paulo), apesar do docstring das
      duas dizer explicitamente "interpretado no fuso America/Sao_Paulo". Uma transação às 22h em
      São Paulo (01h UTC do dia seguinte) caía no dia errado. `update_transaction` e todo `agenda/
      core.py` já usavam `local_date_filter`/`local_date_range_filter` (`tools/postgres/helpers.py`,
      já testados em `tests/tools/postgres/test_helpers.py`) corretamente — só essas duas queries de
      `financeiro/core.py` tinham ficado pra trás nessa migração. Trocado pra reusar os mesmos
      helpers, sem introduzir lógica nova
- [x] Avaliar `fastapi-guard` pra refinamento de segurança da API — integrado em
      `interfaces/api/main.py` (`SecurityMiddleware` + `SecurityConfig`: rate limit próprio, CORS,
      IP banning, detecção de atividade suspeita). Achados corrigidos durante a integração: kwarg
      `rate_limit` duplicado (`SyntaxError`), `cors_allow_credentials=True` com
      `cors_allow_origins=["*"]` (combinação que o CORS spec rejeita — e a API nem usa cookie, é
      `X-API-Key`), `redis_url` faltando (`SecurityConfig` aponta pro Redis local por padrão, não
      pro Redis real do projeto — com `redis_fail_open=False`, isso derrubava toda request com
      `GuardRedisError`). `tests/interfaces/api/conftest.py` desliga o `SecurityMiddleware` no
      fixture `client` (mesmo padrão do `limiter.enabled = False` do slowapi) porque o check
      `ip_security` rejeita o host fake do `TestClient` ("testclient" não é IP). Resultado: 3
      camadas de rate limit hoje coexistem (slowapi/Redis por IP, fastapi-guard por IP, Redis por
      user_id em `chat/service.py`) — redundante mas não quebrado; simplificar é decisão em aberto
- [x] `.env.example` com valores/nomes errados (revisar de novo, além do ajuste já feito na seção
      "Débitos técnicos" acima) — `.env.example` em si já batia 1:1 com todo campo obrigatório de
      `config/settings.py:Settings` (conferido campo a campo, nenhum nome antigo tipo
      `DATABASE_URI`/`MONGODB_URI`/`MONGO_USER`/`MONGO_PASSWORD`/`QDRANT_CLUSTER_ENDPOINT` sobrou em
      lugar nenhum do repo). O gap real estava no README: a lista de variáveis de ambiente (seção
      "Configuração") não incluía `SIGNUP_SECRET` — que é campo obrigatório sem default em
      `Settings`, então `Settings()` falha ao importar sem ele. Quem seguisse só o bloco do README
      (sem abrir `.env.example` também) ficaria travado num erro de import sem saber por quê.
      Adicionado ao bloco + uma linha explicando o que é
- [x] Hash de API key sem salt e sem rotação — **avaliado.** Salt não se aplica aqui: a key
      (`secrets.token_urlsafe(32)`, `interfaces/api/gen_key.py`) já tem 256 bits de entropia
      aleatória, então rainbow table é inviável independente de salt — mesmo padrão usado por
      GitHub/Stripe pra token de alta entropia (`sha256` puro). Rotação: hoje já existe de forma
      implícita via TTL (`API_KEY_TTL_TIME`, 24h) — a key expira sozinha e `POST /v1/keys` libera de
      novo. Endpoint explícito de revogar/rotacionar antes da expiração (útil se a key vazar)
      ficou decidido como não prioritário por ora — decisão consciente, revisar se o projeto sair do
      estágio pessoal/experimental
- [x] Indirect prompt injection via PDF (ingestão de documentos) — **avaliado, sem ação necessária
      por ora.** `tools/qdrant/faq/ingest.py` indexa um único PDF fixo commitado no repo
      (`data/documents/FAQ_assessor_v1.1.pdf`), sem nenhum endpoint de upload em `interfaces/api/` —
      não existe pipeline de ingestão de documento de terceiro não confiável hoje. A ameaça descrita
      pressupõe esse pipeline; construir defesa agora seria especulativo (YAGNI). Revisitar se/quando
      existir upload de documento por usuário
- [x] IDOR e isolamento entre usuários (revisar todos os endpoints, não só chats) — **verificado,
      já coberto.** Superfície completa da API hoje: `health` (sem dado de usuário), `POST /v1/keys`
      (signup público atrás de `X-Signup-Secret`, sem ownership pra checar) e `chats` (já reforçado
      acima). `financeiro`/`agenda` — as duas preocupações levantadas por essa entrada — checadas:
      (1) todo tool schema (`financeiro/schemas.py`, `agenda/schemas.py`) grepado, nenhum expõe
      `user_id` como argumento — o LLM nunca escolhe de quem é o dado, é sempre o `current_user_id()`
      do `ContextVar`; (2) toda query de leitura já filtra por `Transaction.user_id ==
      current_user_id()`/`Event.user_id == current_user_id()` na cláusula `WHERE` (não é checagem
      pós-fetch), e `update_transaction`/`update_event` por id direto comparam `tx.user_id`/
      `event.user_id` contra `current_user_id()` antes de aplicar mudanças; (3) `Category`
      (`tools/postgres/models.py`) não tem `user_id` — é taxonomia compartilhada, não dado privado,
      então atribuir `category_id` de outro registro não vaza nada entre usuários; (4) `user_id` em si
      vem só de `interfaces/api/auth.py:get_current_user` (API key → Redis → user_id), nunca aceito
      como parâmetro do cliente; (5) `send_message`/demais rotas são `def` síncrona rodando via
      threadpool do Starlette (`anyio.to_thread.run_sync`), que copia o `contextvars.Context` por
      chamada — `set_current_user`/`reset_current_user` (`chat/runner.py:executar`) operam sobre uma
      cópia isolada por request, sem vazar entre requisições concorrentes no mesmo processo
- [x] Rate limiting (slowapi, por IP) é bypassable — `Limiter` (`interfaces/api/rate_limiting.py`) não
      tinha `storage_uri`, então usava o backend padrão do `slowapi`/`limits`: contagem em memória
      *por processo*. Com mais de um worker/instância (esperado em prod), cada um mantém seu próprio
      contador — o limite efetivo vira N× o configurado, só por tráfego cair em workers diferentes.
      Corrigido apontando `storage_uri=settings.REDIS_URL` — Redis já é infra compartilhada do
      projeto (`tools/redis`), `redis`/`limits` já instalados (dependência do `slowapi`), sem
      dependência nova. Verificado isoladamente que o `Limiter` conecta no Redis configurado
      (`interfaces/api/main.py` está com WIP não relacionado e sem importar no momento, então os
      testes de `tests/interfaces/api` não rodaram nessa verificação — só o resto da suíte, 80/80)
- [ ] Observabilidade e data leakage no chat runner + repositories (além do gap de PII já registrado
      na seção LangSmith acima)
- [x] Guardrail de saída: fallback de compliance é bypassável — `guardrail_saida`
      (`agents/nodes/guardrail/saida.py`) chamava o LLM de compliance e, se ele não devolvesse o
      formato `RESPOSTA:` esperado, caía direto na resposta original **sem revisão nenhuma** —
      justamente o texto que o guardrail existe pra revisar (garantia de rentabilidade, indicação
      de ativo sem disclaimer, certeza sobre mercado futuro). Corrigido: 1 retry na mesma chamada
      (`_revisar_compliance`, temperatura 0 então falha de formato tende a ser transiente) e, se
      ainda assim falhar, cai num texto seguro genérico (`_FALLBACK_COMPLIANCE`) em vez de repassar
      o conteúdo não revisado — mantém o design "nunca bloqueia" (sempre responde algo), mas fecha o
      bypass. Teste cobrindo o caso de bypass real (LLM nunca segue o formato, resposta arriscada
      não pode vazar) e o caminho feliz: `tests/agents/nodes/guardrail/test_saida.py`
- [x] **Correção de achado anterior:** o item de `MongoDBSaver`/pymongo acima registrava o
      `TLSV1_ALERT_INTERNAL_ERROR` do Mongo Atlas como "resolvido travando `requires-python<3.14`".
      Estava errado — o mesmo erro voltou a derrubar um deploy (`ServerSelectionTimeoutError` nos 3
      shards do cluster) rodando `python3.13` de verdade (confirmado no log de produção,
      `.venv/lib/python3.13/site-packages/pymongo`), então não tinha relação com a versão do Python.
      Causa real: Network Access do Atlas (IP allowlist) não cobria os IPs de egress dinâmicos da
      FastAPI Cloud — corrigido liberando acesso no painel do Atlas, não no código. O pin
      `requires-python<3.14` continua válido pelo motivo original (era necessário por outro motivo),
      só não era a causa desse incidente
- [x] `graph/builder.py:_GrafoLazy` — classe reimplementando memoização manual (`_instancia is
      None`) só pra adiar a criação do `MongoDBSaver`/compilação do grafo pro primeiro uso. Trocado
      por uma função `fluxo_agentes()` com `@functools.cache` (stdlib), mesmo comportamento de
      singleton lazy sem a classe. Call site (`chat/runner.py`) virou `fluxo_agentes().invoke(...)`

## Frontend web (React + Vite + GSAP) — V1 implementada

Interface web consumindo a API que já existe, em `web/` (branch `feat/frontend-web`). Escopo da
V1: login simples (escolher usuário do banco ou criar), tela de chat com sidebar de conversas e
animação nas mensagens / no "pensando". Implementado ponta a ponta e testado contra o backend real
(Mongo/Redis/LLM em nuvem) — falta só a decisão de deploy em produção (ver seção Deploy).

### Tecnologia escolhida

- **React 19 + Vite + TypeScript.** Não Next.js: não há SSR nem SEO em jogo (app atrás de login) e
  Next traria um servidor Node pra deployar ao lado da API FastAPI que já existe. Vite gera estático
  puro, que qualquer coisa serve — inclusive o próprio FastAPI (ver Deploy abaixo).
- **GSAP core + `@gsap/react`** (`useGSAP`). Sem plugins — ScrollTrigger/Flip/SplitText são
  ferramenta de landing page, não de chat. Duas dependências, core ~23kb gz.
- **`react-router`** — rotas `/login`, `/chat`, `/chat/:chatId` (duas rotas em vez de um segmento
  opcional `:chatId?` — mais simples, sem depender de sintaxe específica de versão do router).
- **Estado de servidor: `fetch` + `useState`.** Sem TanStack Query, sem Redux/Zustand — são ~5
  chamadas de API no app inteiro. Adicionar quando houver cache/invalidação de verdade pra gerenciar.
- **Estilo: Tailwind CSS v4 + tokens do design system da Kobana** (`github.com/universokobana/
  kobana-ui`) — **mudou em relação à decisão original deste TODO** ("CSS Modules, sem Tailwind, sem
  lib de componentes"). O pedido explícito de usar o design system da Kobana implica Tailwind, já
  que o Kobana UI é construído sobre shadcn/ui + Tailwind. Investigado: o pacote (`@kobana/ui`, MIT,
  público no npm) não tem primitivos (Button/Input/Card) no próprio repo — só composites de
  back-office (DataTable, FilterBar...) que não servem pra chat — e é consumido via CLI interna que
  copia arquivos, arriscado rodar sem supervisão num agente não-interativo. Decisão: extrair os
  tokens reais do repo (`src/tokens/colors.ts`, `web/styles/underlith.tokens.css` — cores de marca
  `lime #D3FD54` / `black` / `white #FDFDFB` / `gray #676767` / `purple #A630DA`, tipografia Work
  Sans + Syne, radius `0.5rem`) e montar primitivos shadcn-style à mão (`web/src/components/ui/`)
  em cima deles, sem depender da CLI. **Isso também substitui o par cyan/verde do terminal/TUI**
  (ver seção Identidade visual abaixo) — a paleta da Kobana não tem essas cores: lime passou a ser
  a cor do assistente, purple a do usuário.
- **`web/src/components/ui/`** — Button/Input/Card feitos à mão com Tailwind + os tokens acima.
  Sem Radix/cva — poucos componentes, variant via mapa de classes simples (`clsx` +
  `tailwind-merge`, padrão shadcn de merge de classe).

### Onde fica no projeto

**`web/` na raiz, não `interfaces/web/`.** Conceitualmente `interfaces/` é o lugar certo (é mais uma
"forma de uso", ao lado de `terminal`/`tui`/`api`/`a2a`), mas mecanicamente não: `interfaces` é
pacote Python empacotado no wheel (`[tool.hatch.build.targets.wheel] packages = ["config",
"interfaces", "src/assessor_ai"]`). Enfiar um projeto Node ali custa três exclusões de build
(hatch, `.fastapicloudignore`, `.gitignore`) pra ganhar só simetria de nome — e um `node_modules`
indo junto no deploy da API é o tipo de erro que só aparece no build lento.

Isso responde diretamente o item **"Avaliar a estrutura antes de continuar adicionando"** do backlog,
que pediu essa decisão antes de mais um pacote entrar: a divisão vira `config/` + `interfaces/` +
`src/assessor_ai/` (Python) e `web/` (Node), com a fronteira sendo a linguagem, não a camada.

- [x] `.gitignore`: `web/node_modules/`, `web/dist/`
- [x] `.fastapicloudignore`: `web/`
- [x] `ruff` não olha `.ts`/`.tsx`, então `just check` não muda; `just test` idem. Verificação do
      frontend é `npm run build` (TypeScript + Vite) dentro de `web/`; `just web` sobe o dev server

### Gaps da API — bloqueadores, resolvidos antes do front

1. - [x] **`GET /v1/chats` não existe** — a sidebar não tem de onde listar conversas. Precisa de
     `listar_por_usuario(user_id)` em `tools/mongo/chats/core.py` (`find({"user_id": ...})`, projeção
     **sem** `messages`, sort por `updated_at` desc, cap ~50) + `repositories` + `service` + rota +
     schema. **Não existe campo de título** no `ChatDocument` — derivar do primeiro `content` de role
     `human` (truncado em ~40 chars), sem coluna nova. Chat vazio (criado e nunca usado) vira
     "Nova conversa". **Implementado:** `listar_por_usuario` usa `{"messages": {"$slice": 1}}` na
     projeção (só a primeira mensagem, sempre `human` quando o chat não está vazio) em vez de omitir
     `messages` por completo — precisa dela pro título, mas sem carregar o histórico inteiro.
2. - [x] **A tela de login não funciona com o desenho de auth atual.** Com
     `API_KEY_AUTH_ENABLED=false`, `get_current_user` (`interfaces/api/auth.py:15`) devolve sempre
     `obter_usuario_padrao()` — o *primeiro* usuário do Mongo, ignorando qualquer escolha do cliente.
     Com a flag `true`, o caminho seria `POST /v1/keys`, mas ele responde `409` quando o usuário já
     tem key ativa e não reexibe a key salva (só o hash fica) — ou seja, "entrar como um usuário
     existente" quebra nos dois modos.
     **Caminho barato:** com a flag desligada, `get_current_user` aceita um header opcional
     `X-User-Id` e só cai no `obter_usuario_padrao()` se ele faltar. ~4 linhas, sem tocar no caminho
     de API key, que continua inteiro e testado. `ponytail:` isso é bypass de auth deliberado — só
     vale enquanto `API_KEY_AUTH_ENABLED=false`; o caminho real é reativar a API key junto com um
     endpoint de reemissão/revogação (ver "Hash de API key sem salt e sem rotação", seção Segurança).
     **Implementado** exatamente como descrito, em `interfaces/api/auth.py:get_current_user`.
3. - [x] **`GET /v1/users` não existe** — a tela de login precisa listar pra escolher/sortear.
     `mongo/users/core.py:listar()` (`find({}, {"user_id": 1, "nome": 1, "email": 1})`, cap ~50) +
     rota. Só faz sentido em modo dev — gatear pela mesma flag do item 2 (`404` quando a auth por
     API key estiver ligada), senão é enumeração de usuários exposta. **Implementado** em
     `interfaces/api/routes/users.py` (`GET /v1/users`).
4. - [x] **Criar usuário pelo front** — `POST /v1/keys` já resolve por dentro
     (`chat_service.obter_ou_criar_usuario`), mas exige `X-Signup-Secret` e devolve uma API key que o
     modo dev não usa. Um `POST /v1/users` (nome+email → `obter_ou_criar_usuario` → `user_id`), sob a
     mesma flag dos itens 2 e 3, é mais direto que fazer o front carregar o signup secret.
     **Implementado** (`interfaces/api/routes/users.py:create_user`) — reaproveita
     `chat_service.obter_ou_criar_usuario` já existente, sem endpoint novo de repositório.
5. - [ ] **CORS na prática** — `SecurityConfig` (`core/middleware.py`) já tem
     `cors_allow_origins=["*"]` e `cors_allow_methods=["GET", "POST"]`. Falta conferir preflight real
     de browser passando pelo `SecurityMiddleware` do fastapi-guard, que roda `ip_security` antes
     (o mesmo check que `tests/interfaces/api/conftest.py` precisa desligar porque rejeita host que
     não é IP). Em dev isso não aparece — o proxy do Vite deixa tudo same-origin —, então é
     verificação de pré-deploy, não de desenvolvimento
6. - [ ] **Commit + versão do deploy no front** — encaixar no `GET /health/live` (versão via
     `importlib.metadata` + hash curto do commit). Resolve de passagem o item "Versão do projeto está
     em três lugares diferentes e discordando" do backlog, que é pré-requisito disso fazer sentido
7. Fora do caminho crítico da V1, mas registrar a consequência:
     `encerrar_sessao` continua sem endpoint (item já aberto) — quem usa web/API **nunca** gera
     resumo nem perfil. O front não trava sem isso, mas o assistente fica sem memória pra esse
     usuário, que é o mesmo bloqueador já registrado no item de memória episódica

### Telas

- [x] **`/login`** (`web/src/pages/login-page.tsx`) — grid de cards com os usuários do banco, botão
      "entrar com um aleatório" e um form curto "criar novo" (nome + email). Guarda `user_id` no
      `localStorage` (versionado, `assessor-ai:user:v1`) e manda em `X-User-Id`. Sem senha, sem
      sessão — é tela de teste, comentário no topo do arquivo deixa isso explícito
- [x] **`/chat` e `/chat/:chatId`** (`web/src/pages/chat-page.tsx`) — duas rotas em vez do segmento
      opcional `:chatId?` do plano original (ver "Tecnologia escolhida"). Sidebar esquerda (lista de
      chats + botão "novo chat" + usuário atual no rodapé) · painel de mensagens rolável · input
      fixo embaixo. Sem `chatId` na URL, cria o chat no primeiro envio (não na montagem)
- [ ] Sidebar colapsável abaixo de ~768px — **não entrou na V1**, layout só desktop por ora

### Animações (GSAP core + `useGSAP`)

Regra transversal, sem exceção: tudo dentro de `gsap.matchMedia()` com a condição
`reduceMotion: "(prefers-reduced-motion: reduce)"` → `duration: 0`. Acessibilidade não é o lugar de
cortar. Um `mm` por componente, revertido pelo próprio `useGSAP` no unmount.

- [x] **Mensagem entrando** (`components/chat/message-list.tsx`) — `gsap.from` no nó recém-montado:
      `autoAlpha: 0, y: 12, scale: 0.98`, `ease: "power2.out"`, ~0.35s. `useGSAP` com `scope` no
      container do histórico e `dependencies: [mensagens.length]`. `autoAlpha`, não `opacity`
- [x] **Sidebar montando** (`components/sidebar/sidebar.tsx`) — mesma tween com `stagger: 0.04`
- [x] **"Pensando"** (`components/chat/thinking-dots.tsx`) — timeline `{ repeat: -1, yoyo: true }`
      em 3 pontos com `stagger`. **Diferença do plano original:** em vez de guardar o retorno pra
      `.kill()` manual, o componente só existe enquanto `pensando === true`
      (`{pensando && <ThinkingDots />}` em `message-list.tsx`) — o `useGSAP` já reverte/mata a tween
      sozinho no unmount, então desmontar o componente quando a resposta chega já limpa tudo, sem
      guardar timeline numa ref à parte
- [x] **Transição login → chat** (`pages/login-page.tsx`) — fade da tela inteira no clique de
      "Entrar", callback em `contextSafe` (do `useGSAP`), `onComplete` navega pra `/chat`
- [ ] **Pendente até existir streaming: animação de "mandando"** (texto materializando token a
      token). Depende do item "Endpoint de streaming (SSE ou WS)" da seção API. Enquanto não existir,
      "mandando" e "pensando" são o mesmo estado — não inventar uma animação falsa de digitação sobre
      uma resposta que já chegou inteira
- [x] Nunca `useEffect` + `gsap.context()` solto — todo componente animado usa só `useGSAP`

### Deploy

- [x] **Dev:** `vite dev` com proxy de `/v1` e `/health` pra `http://localhost:8000` — mata CORS na
      origem e deixa o item 5 dos gaps só como verificação de pré-deploy. `just web` sobe o dev
      server (`justfile`)
- [ ] **Prod — decidir:** (a) estático em Vercel/Cloudflare Pages, mantendo a API na FastAPI Cloud e
      o CORS ligado; ou (b) `app.mount("/", StaticFiles(directory="web/dist", html=True))` no mesmo
      app FastAPI — um deploy só, zero CORS, mas exige o `dist/` construído no build da FastAPI
      Cloud, que hoje só roda `pyproject.toml`/`uv.lock` e não tem Node. (a) é o de menor atrito;
      (b) só vale se o `dist/` for commitado ou o CI construir antes

**Achado de ambiente (Windows):** `npm run <script>` quebra nesta máquina porque o caminho do
projeto tem `&` (`...Instituto J&F\...`) — o shim `.bin/vite`/`.bin/tsc` (ou `npx`) calcula o próprio
diretório via `dirname`/`cygpath` e trunca o path no `&`, resultando em
`Cannot find module 'C:\Users\...\vite\bin\vite.js'`. Reproduz em PowerShell e Git Bash igual,
porque o `npm run` do Windows sempre passa pelo `cmd.exe` internamente. **Corrigido** nos scripts de
`web/package.json` (`dev`/`build`/`preview`) chamando `node node_modules/<pkg>/bin/...` direto, sem
passar pelos shims — verificado funcionando nos dois shells.

## Identidade visual e design system

Estado atual — o terminal/TUI mantêm a paleta antiga (cyan/verde); o frontend web adotou o design
system da Kobana (`github.com/universokobana/kobana-ui`) a pedido explícito, então as duas paletas
convivem por ora (ver `web/src/styles/tokens.css`) — não houve tentativa de unificar terminal/TUI/web
numa paleta só nesta entrega.

- Nome **Assessor.AI**, figlet `doom` (`interfaces/terminal/display.py:10`) e o mesmo ASCII no topo
  do README
- Terminal/TUI: **cyan = assistente**, **verde = usuário**, cinza = neutro/logs — mesmo par no Rich
  (`interfaces/terminal/display.py`) e no Textual (`interfaces/tui/app.tcss`). Inalterado.
- **Web:** paleta da Kobana — `lime #D3FD54` = assistente, `purple #A630DA` = usuário, `black`/
  `white #FDFDFB`/`gray #676767` como neutros; tipografia Work Sans (corpo) + Syne (headings/
  números); radius base `0.5rem`. Tokens extraídos de `src/tokens/colors.ts` e
  `web/styles/underlith.tokens.css` do repo da Kobana, copiados pra `web/src/styles/tokens.css` e
  mapeados pro Tailwind via `@theme inline` em `web/src/styles/index.css`
- `assets/` tem só `fluxo_agentes_v1.png` (diagrama de arquitetura) — não há logo, marca ou paleta
  escrita em lugar nenhum fora do código

- [x] **Tokens num arquivo único** (`web/src/styles/tokens.css`) — custom properties da Kobana,
      light por padrão (é o default deles) com override em `@media (prefers-color-scheme: dark)`
      (mais simples que um toggle com classe, sem JS de tema na V1)
- [x] **Tipografia:** Work Sans (corpo/UI) + Syne (`font-display`, headings/números) — `body` já
      usa `font-variant-numeric: tabular-nums` (`index.css`), importante pro app financeiro
- [ ] **Contraste AA (4.5:1)** não conferido formalmente nesta entrega — os tokens vêm direto do
      repo da Kobana (já pensados como design system de produção), mas não houve checagem própria
      de contraste pros pares específicos usados aqui (ex. texto sobre `bg-primary`/lime)
- [x] Zero hex espalhado por componente — todo componente usa classes Tailwind resolvidas a partir
      de `tokens.css`, nenhum valor de cor hardcoded em `.tsx`

## Renomear o projeto — mapa de impacto antes de escolher o nome

Intenção registrada: trocar `Assessor.AI` por um nome com identidade melhor. Escolher o nome pode ser
a qualquer momento; **aplicar só depois do frontend**, porque é um rename em ~15 pontos que conflita
com qualquer branch aberta. Frontend V1 saiu (`feat/frontend-web`) — rename segue liberado pra
acontecer, mas **ainda não aplicado**; esta seção é só o plano.

### Nome escolhido: **Zelo**

Das 10 propostas levantadas junto com o frontend (Zelo, Norte, Cofre, Vero, Aporta, Saldo, Trilha,
Fento, Cadência, Lúmen), **Zelo** venceu — curto, remete a cuidado com dinheiro/tempo (os dois
domínios do produto), vira identificador Python válido sem adaptação (`zelo`) e não colide com nada
já usado no código (grep por `zelo`/`Zelo` no repo: zero ocorrências hoje).

### Mapa de impacto (levantado via grep, contagem real)

**Código Python — 66 arquivos importam `assessor_ai`** (pacote em `src/assessor_ai/`, viraria
`src/zelo/`). Lista completa não vai aqui (é ~todo `src/`, `interfaces/`, `tests/` — qualquer
arquivo que faça `from assessor_ai...` ou `import assessor_ai...`); confirmar de novo com
`grep -rl "assessor_ai" --include="*.py"` na hora de aplicar, já que o número muda com o código.

**Config / build:**

- `pyproject.toml` — `name = "assessor-ai"` → `"zelo"`; `description`; `[project.scripts]
  assessor-ai = 'main:main'` → `zelo = 'main:main'`; `[tool.hatch.build.targets.wheel] packages =
  [..., "src/assessor_ai"]` → `"src/zelo"`
- `justfile` — `cmd := "assessor-ai"` → `"zelo"`
- `web/package.json` — `"name": "assessor-ai-web"` → `"zelo-web"` (novo desde o frontend V1, não
  estava no mapeamento original desta seção)

**Superfície visível:**

- `interfaces/api/main.py` — `title="Assessor AI"` (aparece no `/docs` e no OpenAPI)
- `interfaces/a2a/agents/card.py` — nome do `AgentCard` **e**
  `importlib.metadata.version("assessor-ai")`, que quebra junto com o rename do pacote em
  `pyproject.toml` (o `importlib.metadata.version(...)` lê pelo `name` do `[project]`)
- `interfaces/terminal/display.py:10` (figlet `doom`) e o banner da TUI — trocar o texto renderizado
  pelo pyfiglet, não só uma string solta
- `web/index.html` (`<title>Assessor.AI</title>`) e `web/src/pages/login-page.tsx` (`<h1>` com o
  nome) — também novos desde o frontend V1
- README (ASCII + badges), `AGENTS.md`, `CLAUDE.md`, este `TODO.md`

**Fora do repo** (não é edição de arquivo, é ação manual em cada painel):

- Nome do repositório no GitHub (+ atualizar o remote local depois: `git remote set-url origin ...`)
- App na FastAPI Cloud
- Projeto no LangSmith (`LANGSMITH_PROJECT` no `.env`/Infisical — variável em si não muda de nome,
  só o valor)

**Não muda:** nomes de collection do Mongo/Qdrant, tabelas do Postgres e env vars (`POSTGRES_URL`,
`MONGO_URL`, etc.) — nenhum carrega a marca no nome, só o dado.

### Ordem de execução

Tudo num PR só (é um rename mecânico, não faz sentido fatiar em vários PRs que quebram build uns dos
outros até o último merge), mas arquivo a arquivo dentro dele — **nada de `sed`/regex em massa**
(regra do AGENTS.md: dano silencioso que o lint não pega). Ordem que minimiza quebra intermediária:

1. `git mv src/assessor_ai src/zelo` (preserva histórico do arquivo, ao contrário de deletar+criar)
2. `pyproject.toml` (`name`, `[project.scripts]`, `packages`) — sem isso nada mais importa
   (`assessor_ai` deixa de existir como pacote instalável)
3. Os 66 arquivos que importam `assessor_ai` → `zelo`, um a um (`import`/`from` no topo do arquivo,
   só a raiz do path muda — `assessor_ai.chat.service` vira `zelo.chat.service`, resto do caminho
   igual)
4. `justfile`, `interfaces/api/main.py`, `interfaces/a2a/agents/card.py`
5. `interfaces/terminal/display.py` (figlet) + banner da TUI
6. `web/package.json`, `web/index.html`, `web/src/pages/login-page.tsx`
7. README, `AGENTS.md`, `CLAUDE.md`, `TODO.md` (esta seção some/vira "concluído" no lugar)
8. `just check` + `just test` verdes, `web/`: `npm run build` sem erro — só então commit
9. Ações fora do repo (GitHub, FastAPI Cloud, LangSmith) — depois do merge, não antes (evita branch
   órfã se o rename do repo no GitHub acontecer com PR aberto)

- [x] Escolher o nome — **Zelo**
- [ ] Aplicar arquivo a arquivo (nada de `sed` — regra do AGENTS.md), em PR próprio, sem outra
      mudança junto

## Memória: Postgres (curta) + Neo4j (longa) — proposta avaliada, parcialmente aceita

Proposta recebida em 2026-08-25: remover Mongo, mover o checkpointer do LangGraph pro Postgres,
e pôr memória longa (preferências, tom, relações) num Neo4j. Avaliada item a item contra o código
antes de virar trabalho — três das seis premissas não batem com o repo de hoje.

### O que checa — aceito

- **Trocar `MongoDBSaver` por `PostgresSaver`** — é o único item da lista que se sustenta sozinho,
  sem depender de decisão nenhuma em aberto. Tira um serviço em nuvem do caminho crítico de toda
  mensagem e junta o estado do grafo no mesmo banco que já tem transações/eventos (backup e
  restore passam a ser um só). Plano concreto na subseção "Passo 1" abaixo
- **Trim/sumarização do contexto dentro do grafo** — necessário de qualquer jeito: hoje
  `MessagesState` (`graph/state.py`) cresce sem teto e cada turno reenvia o histórico inteiro pros
  especialistas via `mensagens_com_contexto` (`agents/nodes/contexto.py`). Independe de qual banco
  guarda o checkpoint
- **Regras de higiene de memória longa** — origem/data/confiança por fato, só gravar com
  confirmação/declaração explícita/recorrência, editar e apagar por item, nunca guardar raciocínio
  bruto do modelo. Valem qualquer que seja o backend, e são mais restritas (melhor) que o desenho
  atual do item "Memória episódica do usuário" no Backlog, que só previa `{id, texto, data,
  session_id}`. **Adotar esses campos lá**, mesmo sem Neo4j
- **Separar "memória de contexto do agente" de "histórico de produto"** — é a distinção certa e o
  projeto não a fazia explicitamente. Só que a conclusão que a proposta tira dela está invertida
  (ver abaixo)

### O que não checa — premissas erradas

- **"`user_profiles`: perfil é gerado mas nem é injetado nos prompts dos agentes"** — era verdade,
  deixou de ser. `agents/nodes/contexto.py` monta uma mensagem de sistema por turno com
  `perfil_usuario`, e `no_financeiro`, `no_agenda`, `no_orquestrador`, `no_roteador` e `no_faq`
  passaram a consumi-la (`agents/prompts/base.py:82`, `contexto_do_turno`). Está registrado como
  `[x]` no item "`perfil_usuario` é gerado, cacheado e nunca lido" do Backlog. A proposta descreve
  o repo de antes desse fix — o argumento "remover porque ninguém lê" caiu junto
- **"`agent_chats` duplica o checkpointer e não é usado pela interface atual"** — falso pra API,
  A2A e web; verdade só pra terminal/TUI. Quatro endpoints dependem dele: `POST /v1/chats`
  (`create_chat`), `GET /v1/chats` (`listar_chats`, e o título de cada chat sai da primeira
  mensagem, `routes/chats.py:76`), `GET /v1/chats/{id}/messages` (`get_history`) — mais o sidebar
  do front (`web/src/components/sidebar/sidebar.tsx`). Não é duplicação inerte, é o que a UI lê
- **"`get_history()` pode ser atendido pelo checkpointer"** — parcial, e colide com o próprio
  plano. (1) `listar_chats(user_id)` não sai de `graph.get_state()`: exigiria varrer `list()` de
  checkpoints filtrando por `metadata.user_id` (que `chat/runner.py:41` já grava) e deduplicar por
  `thread_id` — mais código que o `find` de hoje, num caminho quente da UI. (2) O checkpointer
  guarda **uma linha por superstep**, não um histórico de conversa. (3) Pior: o mesmo documento
  pede trim/sumarização do `MessagesState` — se o histórico do produto mora no checkpoint, o trim
  apaga o histórico da UI junto. Estado de execução tem ciclo de vida de execução; histórico de
  produto, não
- **Contradição interna do plano** — a última regra já diz "criar uma tabela `chat_messages` só se
  a API precisar de histórico paginado, exportação, auditoria ou analytics". A API **já precisa**
  de listagem e histórico, hoje. Então o passo 2 não é "remover `agent_chats`": é "migrar
  `agent_chats` de Mongo pra uma tabela `chat_messages` no Postgres". O trabalho não some, troca de
  banco — e isso muda a estimativa do passo inteiro
- **A modelagem Neo4j é de outro domínio** — `(:Ingredient {name:"lactose"})`,
  `(:Cuisine {name:"italiana"})`, "preferências alimentares", "restrições",
  `[:COMPARTILHA_ESTOQUE_COM]->(:Household)`. Este projeto é assessoria de **finanças e agenda**:
  não existe casa, estoque, ingrediente nem receita no domínio, nem no backlog. O exemplo veio de
  um projeto de despensa/cozinha. Como o argumento pró-grafo é justamente "as relações importam", e
  as relações citadas não existem aqui, o item fica **sem justificativa** até estar escrito quais
  relações do domínio real (usuário ↔ categoria de gasto ↔ recorrência ↔ evento de agenda?)
  precisam de travessia de grafo que Postgres + Qdrant não dão
- **"Remover resumo/perfil ao encerrar sessão"** — o efeito prático é menor do que parece, e o
  bloqueador é outro: `encerrar_sessao` só é chamado por `interfaces/terminal/app.py` e
  `interfaces/tui/app.py`. **A API nunca chama** (já registrado no Backlog). Quem usa API/A2A/web já
  não gera perfil nenhum. E qualquer memória longa — Neo4j ou não — esbarra no mesmo buraco: não
  existe gatilho decidido. Decidir o gatilho vem antes de escolher banco

### Custo escondido no passo 1 que a proposta não menciona

`langgraph-checkpoint-postgres` roda em **psycopg 3** (`psycopg[binary]`); o projeto usa
`psycopg2==2.9.11` com SQLAlchemy (`tools/postgres/connection.py:39`). Trocar o checkpointer não
remove uma dependência, **adiciona** um segundo driver de Postgres no mesmo processo. Duas saídas:
conviver com os dois (mais simples agora, dois pools), ou mover o SQLAlchemy pra psycopg 3 junto
(`postgresql+psycopg://` na `POSTGRES_URL`) e deletar o psycopg2 — um driver só, mas mexe na URL
que vem do Infisical e em todo o caminho de ORM já testado. Ver decisão no Passo 1.

Segundo custo: `PostgresSaver.setup()` cria as tabelas dele (`checkpoints`, `checkpoint_blobs`,
`checkpoint_writes`, `checkpoint_migrations`) **fora do Alembic**, no mesmo banco que o Alembic
versiona. Duas fontes de schema convivendo — aceitável (é schema de biblioteca, não do domínio),
mas precisa ficar escrito pra ninguém tentar "consertar" gerando migration em cima delas. Se
incomodar, o isolamento barato é um schema Postgres separado, não migration própria.

### Ordem revisada

1. [ ] **`MongoDBSaver` → `PostgresSaver`** — aceito como está, plano abaixo. Não depende de nada
2. [ ] **Trim/sumarização do `MessagesState` dentro do grafo** — subiu de posição: independe do
       banco, e é o que impede o custo por turno de crescer sem teto. Fazer antes de qualquer coisa
       de memória
3. [ ] **Decidir o gatilho de escrita de memória** (endpoint de encerrar sessão / TTL de sessão
       inativa / extração por turno fora do caminho crítico). Bloqueia 4 e 6, e já bloqueava o item
       "Memória episódica do usuário" do Backlog. É decisão escrita, não código
4. [ ] **`agent_chats` → tabela `chat_messages` no Postgres** — migração, não remoção (a UI lê).
       Só aqui o Mongo fica realmente vazio e o `pymongo` pode sair. Depende de 1
5. [ ] **`user_profiles`** — não remover; migrar junto de 4, com os campos de origem/data/confiança
       da proposta. Removê-lo hoje regride o contexto que os especialistas já usam
6. [ ] **Neo4j Agent Memory** — aceito como destino da memória longa, só a camada `long-term`.
       Depende de (3). Ver subseção "Neo4j Agent Memory" abaixo — a primeira avaliação desta
       seção julgou "Neo4j como banco de grafo" e estava errada sobre o produto
7. [ ] **Async / `AsyncPostgresSaver`** — mantido como estava: o item "Async no máximo possível" do
       Backlog já concluiu que o ganho é **zero** até existir consumidor async de verdade (streaming
       SSE), porque o grafo é sequencial por desenho e a rota `def` já usa o threadpool do Starlette.
       Trocar `PostgresSaver` por `AsyncPostgresSaver` é troca de classe quando chegar a hora — não é
       motivo pra fazer o passo 1 diferente

### Neo4j Agent Memory — avaliado de verdade (corrige a primeira leitura)

<https://neo4j.com/labs/agent-memory/> — não é "usar Neo4j como banco", é uma lib de memória
pronta. A primeira avaliação desta seção rejeitou o item com dois argumentos que **não se
sustentam** contra o produto real:

- "o trabalho está fora do banco, o grafo não ajuda na extração" — **falso**: a lib traz o
  pipeline de extração (spaCy → GLiNER → LLM, cada estágio liga/desliga por config) com
  deduplicação de entidade embutida. Era exatamente o passo caro que a avaliação dizia sobrar
- "falta invalidação temporal, que seria o argumento a favor" — a camada `long-term` tem
  **temporal fact validity**. O critério de reabertura que a própria avaliação escreveu já estava
  atendido

Custos levantados que também caem: **provider** não é preso a OpenAI (extras `google`/`vertex-ai`
nativos + fallback LiteLLM que cobre Groq — o Gemini/Groq daqui encaixa sem provider novo); **peso
de dependência** não é problema (spaCy e GLiNER são extras opcionais, `enable_spacy`/`enable_gliner`/
`enable_llm_fallback`; base + extração LLM-only não puxa torch pro deploy); **vetor** não duplica o
Qdrant (vector + graph no mesmo store, e o Qdrant continua só com o FAQ).

**O que sobrou de risco real, bem menor:**

- Versão `0.2.x`, Neo4j **Labs**, sem compromisso de estabilidade de API documentado. Num repo que
  pina ~100 deps em `==` e que já pagou o preço do `a2a-sdk` divergindo do tutorial oficial (ver
  item A2A no Backlog), isso é risco de verdade. Mitigação: pin exato, e a memória ter que ser
  **degradável** — se a lib quebrar, o assistente piora, não cai. Isolar atrás de uma função só
  (mesmo padrão de `tools/qdrant/faq/core.py`, que já devolve `Response.error` sem derrubar o nó)
- NAMS (hosted) é **preview, sem preço divulgado** — então self-host num Aura, o que devolve o
  quinto serviço em nuvem. Custo honesto, não impeditivo
- **Ligar só a camada `long-term`.** A `short-term` duplica o checkpointer (a proposta original já
  dizia isso, e estava certa) e a `reasoning` (trace de tool/decisão) sobrepõe o LangSmith, que já
  está ligado e redigindo PII (`chat/repositories.py`). Ligar as três é pagar duas vezes por coisa
  que existe
- Requisitos: Neo4j 5.20+ self-hosted (5.11+ pra vector search), Python 3.10+ (o repo é 3.13, ok).
  Os 8 schemas de domínio que a lib traz (podcast, news, medical, legal...) **não incluem
  finanças/agenda** — vai ser schema custom ou o caminho genérico

**O que não muda: a ordem.** A lib dá extração e storage; ela **não decide quando chamar `add`**. O
gatilho (passo 3) continua sendo o bloqueador, e `encerrar_sessao` segue sem ser chamado pela API.
Mas a decisão encolheu: com extração barata e fora do caminho crítico, o gatilho provavelmente
resolve pra "por turno, depois da resposta já ter saído" — que é onde o item "memória não vira tool
do roteador" do Backlog já tinha chegado por outro caminho. Deixou de ser decisão de arquitetura e
virou "onde chamo isso dentro de `chat/service.py:send_message`".

### Passo 1 — plano de execução (`MongoDBSaver` → `PostgresSaver`)

**Decisão de driver:** conviver com psycopg2 + psycopg3 nesta etapa. Unificar em psycopg 3 é um PR
separado, com teste de todo o caminho de ORM, e não é pré-requisito. Motivo: manter o diff do passo 1
restrito a `graph/builder.py` — se o checkpointer der problema, o rollback é uma linha, não uma
migração de driver.

1. **Dependência** — `uv add "langgraph-checkpoint-postgres" "psycopg[binary,pool]"`. Conferir que o
   resolver não mexeu nos pins de `langgraph==1.1.6` / `langgraph-checkpoint==4.0.2`
2. **Pool** — em `tools/postgres/connection.py`, um `ConnectionPool` psycopg3 lazy, no mesmo padrão
   `global` + `_get_session_factory()` que já existe ali (e entrando no `dispose_engine()`, que a API
   já chama no `lifespan` de shutdown). Obrigatório pelo driver:
   `kwargs={"autocommit": True, "row_factory": dict_row}` — sem `autocommit` o `setup()` não
   persiste as tabelas, sem `dict_row` o checkpointer quebra ao ler as linhas.
   **Não usar `PostgresSaver.from_conn_string()`**: é context manager, fecha a conexão na saída do
   `with` — morre no primeiro uso dentro de um app de vida longa
3. **Builder** — `graph/builder.py:fluxo_agentes()` troca o `MongoDBSaver` por `PostgresSaver(pool)`
   + `checkpointer.setup()` na mesma função. O `@cache` que já está lá garante que roda uma vez por
   processo, que é exatamente o contrato do `setup()` (idempotente, mas caro). Aproveitar o mesmo
   commit pra deletar as 3 linhas mortas de `LANGGRAPH_ALLOWED_MSGPACK_MODULES` (env var que o
   langgraph não lê — só existe `LANGGRAPH_STRICT_MSGPACK`) e o `warnings.filterwarnings` no-op de
   `chat/runner.py:10` (o aviso sai por `logger.warning`, não pelo módulo `warnings`)
4. **Estado antigo** — os checkpoints em Mongo **não** são migrados: são estado de conversa de
   desenvolvimento, e o histórico que a UI mostra vem de `agent_chats`, que este passo não toca.
   Efeito prático: sessões abertas perdem o contexto de execução na virada. Se um dia precisar
   preservar, o caminho é `list()` no saver antigo + `put()` no novo, script descartável
5. **Mongo continua vivo** — `agent_chats`, `user_profiles` e `pymongo` só saem no passo 4 da ordem
   acima. Este passo **não** remove o Mongo do projeto, só do checkpointer
6. **Verificação** — `just check` e `just test` (a suíte não toca no checkpointer real:
   `test_runner.py` patcha `fluxo_agentes`, então tem que seguir verde sem alterar teste). O que
   realmente prova é o teste manual ponta a ponta: `just dev` → duas mensagens encadeadas ("meus
   gastos de ontem" → "e de hoje?") conferindo que a segunda enxerga a primeira, e depois conferir as
   4 tabelas criadas no Postgres. Sem isso, "passou nos testes" não significa nada aqui

## Backlog novo — a triar

Levantado em 2026-08-20, ainda sem investigação. Cada item vira seção própria (ou entra na seção
existente correspondente) quando sair do "a triar".

- [x] **`perfil_usuario` é gerado, cacheado e nunca lido** — corrigido — o campo existe no `Estado`
      (`graph/state.py:24`) e é preenchido a cada mensagem por `chat/runner.py:33` (que busca no
      Mongo com cache Redis), mas **nenhum nó do grafo consome**. `no_financeiro`, `no_agenda` e
      `no_roteador` invocam seus agentes só com `estado["messages"]`; os `system_prompt` são fixos,
      montados em `create_agent` (`graph/agents.py`) na compilação. Ou seja, todo o pipeline de
      perfil (2 chamadas de LLM no `/exit` + cache de 1h) é trabalho jogado fora hoje. É a causa raiz
      do cenário "quanto gastei na viagem pra Maceió": mesmo que a memória existisse, o especialista
      não veria. **Corrigido:** `agents/nodes/contexto.py` (novo) monta uma mensagem de sistema por
      turno com data/hora, perfil e pergunta encaminhada, e `no_financeiro`, `no_agenda` e
      `no_orquestrador` passaram a usá-la no `.invoke()`. Roteador e FAQ entram no mesmo bloco, com
      recorte próprio: o roteador usa `incluir_pergunta=False` (a pergunta encaminhada é saída dele,
      devolvê-la só polui o prompt que o regex `ROUTE=` lê), e o FAQ monta a mensagem de sistema
      direto com `contexto_do_turno(perfil)` porque substitui o histórico pela `pergunta_original` em
      vez de anexá-lo. Quando a memória episódica existir, ela entra nesse mesmo bloco, sem tocar em
      nó nenhum
- [x] **`pergunta_original` só é usado pelo FAQ** — corrigido para financeiro e agenda — o router extrai e publica no estado
      (`nodes/router.py:52`), mas só `no_faq` lê (`nodes/faq.py:9`). Financeiro e agenda ignoram e
      recebem `estado["messages"]` cru. O "protocolo de encaminhamento" do `RouterPrompts` existe,
      mas dois dos três destinos não usam. **Corrigido:** financeiro e agenda recebem a pergunta
      encaminhada no bloco de contexto do turno, mantendo o histórico completo (a conversa importa
      pro fluxo de clarificação, então não dá pra substituir as `messages` pela pergunta como o FAQ
      faz). Agora que os destinos leem o que o roteador manda, um campo novo de instrução
      (`CONTEXTO=` ao lado do `PERGUNTA_ORIGINAL=`) passa a fazer sentido — antes viraria um terceiro
      campo ignorado
- [x] **`CONTEXTO_TEMPORAL` congela na hora do import** — corrigido — `agents/prompts/base.py:3` calcula
      `_agora = datetime.now(UTC).astimezone()` no escopo do módulo e interpola num f-string de
      classe, então "data e hora atual" é a hora em que o processo subiu. Terminal e TUI reiniciam a
      cada uso e mascaram isso; a **API fica com "hoje" travado na data do deploy**, e todo cálculo
      de data relativa ("mês passado", "semana que vem", "ontem") passa a ser feito a partir dela.
      Bate direto em qualquer feature que dependa de data. **Corrigido:** virou
      `GenericAgent.contexto_temporal()`, avaliada na chamada, e saiu do `system_prompt()` — deixar
      lá não resolveria nada, porque `graph/agents.py` chama `system_prompt()` uma vez só, no import.
      A data agora chega pelo bloco de contexto do turno. Teste de regressão em
      `tests/agents/test_contexto.py` patcha o `datetime` do módulo: se a data voltar a ser
      constante calculada no import, o patch não surte efeito e o teste quebra
- [ ] **Decidido: memória não vira tool do roteador** — a ideia de escrever memória por turno (em vez
      de só no `/exit`) é boa, mas o roteador é o pior lugar: a saída dele é parseada por regex
      (`ROUTE=` / `PERGUNTA_ORIGINAL=`, `nodes/router.py`), num llama a temp 0 — dar tool-calling
      pra ele faz o modelo alternar entre chamar tool e responder no formato, que é o jeito clássico
      de quebrar o parser. Além disso põe +1 round-trip de LLM em toda mensagem, inclusive "oi", no
      caminho crítico da resposta. Escrita de memória é side effect, não precisa de decisão do LLM:
      o lugar barato é `chat/service.py:send_message` depois da resposta já ter saído, ou a fila de
      tasks. **Leitura**, sim, pode ser tool — mas do especialista (`buscar_memoria("viagem
      Maceió")` na mão do financeiro, que é quem sabe que precisa de data pro filtro), não do router,
      que decide rota e não estratégia de consulta
- [ ] **Memória episódica do usuário (fato, não traço)** — hoje o `profile` guarda só traço estável
      (tom, objetivos, preferências, contexto de vida) porque o `PerfilPrompt`
      (`agents/prompts/resumidor.py`) **proíbe explicitamente** fato episódico ("NUNCA inclua
      saldos, valores ou transações"). Resultado: "viajou pra Salvador em março", "gosta de X",
      "fez Y no dia Z" nunca entram em lugar nenhum. Desenho proposto, sem tocar no grafo:
      (1) campo separado `memories` no `UserDocument` (`tools/mongo/users/schemas.py`), lista de
      `{id, texto, data, session_id}` — **não** misturar no `profile`, a separação é o que resolve o
      problema: traço se reescreve, fato se acumula; (2) `_extrair_memorias(resumo, memorias_atuais)`
      em `tools/mongo/helpers.py`, mesmo padrão de `_gerar_resumo`/`_gerar_perfil`, com prompt novo
      em `resumidor.py` — recebe as memórias existentes pra deduplicar e devolve só as novas;
      (3) append com `$push`, **nunca** rewrite por LLM (o `profile` já sofre disso: reescrever o
      texto inteiro a cada sessão perde informação); (4) injeção sem mexer em nó nenhum —
      `chat/repositories.py:buscar_perfil` passa a concatenar perfil + últimas N memórias no mesmo
      `perfil_usuario` que já vai pro estado. Cap em N (~20) por enquanto; quando não couber mais no
      prompt, o upgrade é busca semântica no Qdrant (embedding já existe pro FAQ). A "aba" é
      `GET /v1/me/memories` + `DELETE /v1/me/memories/{id}` filtrando por `user_id`, só quando o
      frontend existir.
      **Bloqueador que vem antes:** `encerrar_sessao` — único gatilho de resumo/perfil — só é chamado
      por `interfaces/terminal/app.py` e `interfaces/tui/app.py`. **A API nunca chama**, não existe
      endpoint pra isso. Ou seja, hoje quem usa a API já não gera perfil nenhum, e memória construída
      nesse mesmo gatilho nasceria morta pra API, A2A e frontend. Decidir o gatilho primeiro:
      endpoint explícito de encerrar sessão, TTL de sessão inativa, ou extração incremental por turno
      (que é o item da fila de tasks acima). Custo a considerar: +1 chamada de LLM por encerramento e
      um prompt que cresce a cada turno com as N memórias
- [ ] **Versão do projeto está em três lugares diferentes e discordando** — tag git `1.0.0`
      (no commit `965e33f`), `pyproject.toml` `version = "0.1.0"` e o app FastAPI
      (`api/app.py`) `version="0.5.0"`, que é o número que aparece no `/docs` e no
      OpenAPI. Escolher o `pyproject.toml` como fonte única e fazer o FastAPI ler dali
      (`importlib.metadata.version("assessor-ai")`) resolve dois dos três; a tag passa a ser
      consequência do release, não um número solto. Pré-requisito pra qualquer coisa de changelog/
      release notes fazer sentido
- [x] **Avaliar a estrutura antes de continuar adicionando** — decidido e executado em 2026-09-04
      (ver "Estrutura por camada no fluxo de chat" no topo): tudo passou pra dentro de
      `src/assessor_ai/`, `interfaces/` foi dissolvido (A2A e TUI viraram pacotes de topo, no mesmo
      nível de `api/`), e o fluxo de chat virou `api/` → `services/` → `repositories/` + `schemas/`.
      O ponto (4) — `chat/service.py` virando god module — continua de pé sob o nome novo
      (`services/chat_service.py`), agora só mais visível. Texto original do item abaixo:

      **Avaliar a estrutura antes de continuar adicionando** — a maior parte do backlog abaixo
      (A2A, fila de tasks, MCP, frontend, sessões) adiciona pacote novo, então vale decidir a
      estrutura **antes**, não depois de cinco features enfiadas no formato atual. Pontos concretos
      pra revisar: (1) hoje são três pacotes de topo (`config/`, `interfaces/`, `src/assessor_ai/`) —
      dois fora do `src/`, o que já aparece explícito no `[tool.hatch.build.targets.wheel]`; unificar
      tudo sob `src/assessor_ai/` ou assumir a divisão de vez; (2) `interfaces/a2a/` entrou sem
      seguir o padrão dos outros `interfaces/*` (nem sei ainda se A2A é "interface" ou consumidor de
      `chat/service.py`); (3) fila de tasks e MCP não têm lugar óbvio no corte atual —
      `tools/<sistema>/<domínio>/` é pra integração de dado, não pra infra de execução;
      (4) `chat/service.py` é o único ponto por onde tudo passa: conferir se ainda cabe ou se
      começou a virar god module. Resultado esperado é uma decisão escrita (refatora / não refatora /
      refatora só X), não um refactor grande de uma vez — se der pra continuar sem mexer, melhor
      ainda.
      **Primeira decisão escrita (frontend):** o front vai em `web/` na raiz, fora de `interfaces/` —
      a fronteira de pacote passa a ser a linguagem (Python: `config/`, `interfaces/`,
      `src/assessor_ai/`; Node: `web/`), não a camada. Justificativa na seção "Frontend web" acima.
      Os pontos (1), (2), (3) e (4) seguem em aberto
- [ ] **Sessões ativas no Redis** — ver e gerenciar sessões ativas (listar, inspecionar, encerrar)
      usando o Redis que já é infra do projeto. Casa com o item pendente "Cache de sessão" da seção
      Redis acima
- [x] **API key: desativar por ora** — implementado como flag, não remoção: `API_KEY_AUTH_ENABLED`
      (`config/settings.py`, default `true`). Com `false`, `get_current_user`
      (`interfaces/api/auth.py`) para de checar `X-API-Key` em `/v1/chats` e devolve
      `chat_service.obter_usuario_padrao()` — reaproveita o primeiro usuário existente ou cria um
      mock, o mesmo bootstrap que terminal/TUI já usam (extraído de `iniciar_sessao`, que agora só
      chama essa função + `create_chat`, sem duplicar a lógica). O código de auth continua inteiro e
      testado (`tests/interfaces/api/test_auth.py`) — reativar é só voltar a env var pra `true`, não
      precisa mexer em código. **Escopo:** só `/v1/chats`. `POST /v1/keys` continua exigindo
      `X-Signup-Secret` (`verify_signup_secret`) — gerar chave não é o que atrapalha o A2A, não fazia
      sentido desligar
- [ ] **Erro do Llama: trocar o modelo** — causa provável já identificada: a Groq
      descontinuou o `llama-3.3-70b-versatile` (modelo decomissionado devolve erro na chamada, não é
      bug de código). É troca de string, em 2 arquivos: `config/models.py`
      (`Model.LLAMA_3_3_VERSATILE` + entrada no `PROVIDER_MAP`) e `graph/llm.py:38-39`
      (`llm_groq` temp 0.7 e `llm_rapido` temp 0.0). Quem quebra: `llm_rapido` é router,
      orquestrador, FAQ, guardrail de **saída** e os dois LLMs de `tools/mongo/helpers.py`
      (`_gerar_resumo`/`_gerar_perfil`, que rodam no `/exit`); `llm_groq` é só o **fallback** de
      `llm_especialista` — ou seja, financeiro e agenda continuam funcionando no Gemini e só
      descobrem o problema no dia em que o Gemini falhar. Guardrail de **entrada** não é afetado
      (roda em Gemini). A troca muda comportamento de prompt: revisar depois as saídas que dependem
      de formato exato — `ROUTE=...` do router e `RESPOSTA:` do guardrail de saída. **Conferir junto:** `Model.QWEN_2_5_PRO` está
      mapeado como `"qwen-2.5-pro"` no provider `groq` e esse id não parece existir na Groq — nenhum
      agente usa hoje, mas é entrada morta ou errada. Não consegui listar o catálogo vivo da Groq pra
      recomendar o substituto: `GET /openai/v1/models` com a `GROQ_API_KEY` do `.env` local devolve
      403 (a key real vem do Infisical em runtime, `just dev`) — rodar a listagem com a key boa antes
      de escolher
- [x] **A2A: incluir e expor na rota** — implementado, primeira versão. `interfaces/a2a/` deixou de
      ser WIP vazio: `agents/capabilites.py` (a `AgentSkill` única, `financas-e-agenda`),
      `agents/card.py` (o `AgentCard`, versão lida de `importlib.metadata` em vez de hardcoded — não
      é um quarto número desencontrado pro item de versão acima), `agents/interface.py`
      (`AssessorAgentExecutor`, ponte pro `chat/service.py` — mesma camada de terminal/TUI/API,
      arquitetura não foi furada) e `main.py` (`montar_rotas(app)`). Montado no **mesmo app FastAPI**
      de `interfaces/api/main.py` (não é um segundo servidor/ASGI/modo novo em `main.py`) — expõe
      `GET /.well-known/agent-card.json` e `POST /a2a` (JSON-RPC, método `SendMessage`). Cada
      `context_id` do protocolo vira uma sessão/usuário do Assessor via `chat_service.iniciar_sessao()`
      (mesmo bootstrap que terminal/TUI já usam — reaproveita usuário existente), guardado num dict
      em memória (`ponytail:` global, perdido no restart / não compartilhado entre workers — troca
      por Redis, mesmo padrão de `tools/redis/chat.py`, se rodar com múltiplos processos).
      `LimiteDeMensagensExcedido` vira texto de resposta (não erro de protocolo), consistente com o
      429 que a rota HTTP já faz. Sem autenticação de propósito (ver item "API key" acima) e sem
      streaming/tasks (`AgentCapabilities(streaming=False)`) — é resposta imediata de mensagem única,
      que é o que o protocolo já suporta sem precisar de `TaskStore` persistente.
      **Achados que corrigem os dois desta entrada:** (1) o medo de "async-only" não se confirmou na
      prática — só o `AgentExecutor.execute()` (borda) é `async def`; ele chama
      `chat_service.send_message` (síncrono) via `asyncio.to_thread`, exatamente o padrão que o item
      "Async no máximo possível" já recomendava, sem tocar em nó nenhum do grafo; (2) o pacote
      instalado (`a2a-sdk==1.1.2`) precisava mesmo do extra — resolvido trocando a dependência pra
      `a2a-sdk[fastapi]` (`pyproject.toml`), que já inclui `sse-starlette`. **Divergência da doc/tutorial
      oficial:** essa versão do SDK não tem `a2a.server.apps.A2AStarletteApplication`/
      `AgentCard`/`AgentSkill` em Pydantic — os tipos (`AgentCard`, `AgentSkill`, `Message`, `Part`,
      `Role`, ...) são classes protobuf geradas (`a2a.types`, de `a2a_pb2`), e o mount é
      `add_a2a_routes_to_fastapi` + `create_agent_card_routes`/`create_jsonrpc_routes`
      (`a2a.server.routes`) em vez de instanciar um app pronto. Método JSON-RPC também mudou: é
      `SendMessage` (PascalCase, nome do gRPC), não `message/send` do tutorial. Testado
      (`tests/interfaces/api/test_a2a.py`, mock de `chat_service`): card, happy path, reuso de sessão
      por `context_id` e o caminho de rate limit. **Não verificado nesta rodada** (não tem outro
      agente A2A pra testar contra): a preocupação original de chamada recursiva Assessor → outro
      agente → Assessor não se aplica ainda — o Assessor só **recebe** chamadas A2A hoje, não faz
      nenhuma de saída
- [x] **Erro do Llama: trocar o modelo** — confirmado na doc oficial
      (`console.groq.com/docs/deprecations`): `llama-3.3-70b-versatile` (junto com
      `llama-3.1-8b-instant`) foi desligado em 16/08/2026, substituto recomendado pela própria Groq
      é `openai/gpt-oss-120b`. Trocado em `config/models.py` (`Model.GPT_OSS_120B` +
      `PROVIDER_MAP`) e `graph/llm.py` (`llm_groq` temp 0.7, `llm_rapido` temp 0.0). Além da troca de
      string, `build_llm` passou a setar `reasoning_format="hidden"` pra provider `groq` — gpt-oss é
      modelo de raciocínio, sem isso o chain-of-thought viria dentro do `content` e quebraria os
      regex de `ROUTE=` (router) e `RESPOSTA:` (guardrail de saída), que é exatamente o risco que
      este item já apontava. `just check` e `just test` (136 testes) verdes depois da troca.
      **Ainda falta:** `Model.QWEN_2_5_PRO` continua mapeado como `"qwen-2.5-pro"` no provider
      `groq` e esse id não existe no catálogo da Groq — nenhum agente usa hoje, mas é entrada morta
      ou errada, revisar/remover separadamente.
- [ ] **A2A: incluir e expor na rota** — `interfaces/a2a/` existe como WIP mas os 6 arquivos estão
      **vazios** (0 byte), então não há nada implementado ainda. Verificar se a chamada
      Assessor → outro agente → Assessor não fica recursiva. Dois achados de investigação:
      (1) o `a2a-sdk` é **async-only** — `AgentExecutor.execute`/`cancel` são `async def`, servidor é
      ASGI, client é httpx async; não existe caminho sync, então o adaptador A2A é exatamente onde o
      projeto síncrono encosta no async (ver item de async abaixo); (2) o pacote está instalado sem o
      extra de servidor HTTP — `import a2a.server.routes` quebra hoje com
      `ModuleNotFoundError: No module named 'sse_starlette'`. Precisa de `a2a-sdk[http-server]` (ou
      `sse-starlette` explícito) antes de expor qualquer rota
- [ ] **Error handler de sessão** — tratamento de erro dedicado pra sessão (e demais falhas hoje
      caindo no catch-all `500` das rotas)
- [ ] **Fila de tasks** — pra orquestrar execução de tools e sessões fora do request/response
- [ ] **Async no máximo possível** — sem regredir performance; hoje as rotas são `def` síncrona de
      propósito porque o I/O é bloqueante (ver `.agents/skills/fastapi.md`). Só migrar o que tiver
      driver async de verdade. **Investigado (2026-08-20), separando duas coisas que se confundem:**
      (a) *chamar o grafo de dentro de código async* já funciona hoje sem tocar em nó nenhum —
      testado: `await app.ainvoke(...)` com nó `def` roda o nó numa thread do executor e o
      `ContextVar` de `user_id` **propaga** pra essa thread (é a parte que poderia furar o escopo por
      usuário e não fura); (b) *o grafo ser async de verdade* (nós `async def`, `llm.ainvoke`, tools
      async, asyncpg no lugar de psycopg2) é a reescrita grande já registrada na seção do
      `MongoDBSaver`. Ponto que decide a prioridade: async **não** dá paralelismo entre os agentes —
      o grafo é sequencial por desenho (guardrail → router → especialista → orquestrador →
      guardrail), async só libera a thread pra atender *outra* request, e a rota `def` já entrega
      isso via threadpool do Starlette. Ou seja, ganho real é zero até existir consumidor async
      (A2A ou streaming SSE). Quando existir, o caminho barato é `asyncio.to_thread(...)` /
      `ainvoke` na borda, não converter o grafo. Detalhe: `MongoDBSaver.aget_tuple`/`aput` são
      `run_in_executor` em cima do pymongo síncrono, então nem por ali o checkpoint fica async de
      fato. Paralelismo entre especialistas, se um dia quiser, é fan-out de edge no LangGraph — não
      depende de async
- [ ] **Cache no Qdrant** — deixar a consulta do FAQ mais rápida (Redis na frente do retriever)
- [ ] **MCP no lugar de tools** onde for melhor — provavelmente nas tools de consulta de dados
- [ ] **Frontend** — saiu do "a triar": virou a seção **"Frontend web (React + Vite + GSAP)"** acima,
      com tecnologia escolhida, onde fica no projeto, os gaps de API que bloqueiam e o plano de
      animação. "Pegar o commit do deploy e exibir no front" está lá como gap 6, amarrado ao item de
      versão desencontrada
- [x] **Dependabot** — `.github/dependabot.yml` com dois ecossistemas: `uv` (lê o `uv.lock`) e
      `github-actions` (o CI tem `actions/checkout@v4` e `setup-uv@v5` envelhecendo em silêncio).
      Mensal e agrupado porque são ~100 deps pinadas em `==`; major fica fora do grupo, em PR
      individual (langchain/langgraph quebram API entre majors). O CI já roda ruff + pytest em PR,
      então cada PR do Dependabot chega verificado. **Passo manual pendente:** ligar "Dependabot
      security updates" em Settings > Code security do repo — alerta de vulnerabilidade não se
      configura pelo arquivo e ignora o schedule mensal
- [x] **Skill de Mongo** (`.agents/skills/mongo.md`) — primeira leva de pegadinhas já pagas em
      incidente: `MongoClient` é lazy mas `MongoDBSaver.__init__` conecta (cria índices), por isso
      `fluxo_agentes()` é `@cache`; `ServerSelectionTimeoutError` em deploy é allowlist do Atlas e
      não versão de Python/TLS (dois diagnósticos errados registrados neste TODO); o pin
      `pymongo<4.17` vem do `langgraph-checkpoint-mongodb`; `$slice` na projeção; filtro por
      `user_id` na query. Qdrant/Alembic/Textual ficam sem skill até morderem — a regra do AGENTS.md
      é skill de achado real, não tutorial preventivo
- [ ] **Skills mais restritas e descritivas pros agentes** — adicionar novas e apertar as existentes
- [ ] **Dump SQL em `data/`** — "backup" em SQL do schema gerado pelo Alembic
- [ ] **Verificar se IDOR é possível** — já tem entrada `[x]` na seção Segurança; revalidar com a
      superfície nova (A2A, sessões, frontend)
- [x] **Trazer a skill oficial de FastAPI** (repo oficial, com as melhores práticas) pra
      `.agents/skills/fastapi.md` — feito: o arquivo agora tem duas partes, "práticas oficiais"
      (adaptadas ao repo, com exemplos das rotas daqui) e "pegadinhas deste repo" (as 3 originais,
      intactas). Inclui uma seção de **divergências deliberadas** do skill oficial — SQLModel (aqui
      é SQLAlchemy + Alembic, não migrar), rotas `async` (aqui é `def` de propósito) e Asyncer (não
      é dependência). Os arquivos de referência oficiais (`dependencies.md`, `responses.md`,
      `streaming.md`, `path-operations.md`, `pydantic.md`, `other-tools.md`) já estavam em
      `.agents/skills/` e agora são linkados a partir do `fastapi.md`
- [ ] **Alinhar `api/` com a skill do FastAPI** — três divergências concretas do código
      atual, todas registradas na skill: (1) dependências no estilo antigo
      (`user_id: str = Depends(get_current_user)`) em vez de `Annotated` + alias `CurrentUserDep`
      (`api/routes/chats.py`, `api/auth.py`); (2) `response_model=X` onde a anotação de retorno
      bastaria — as rotas de chats já ganharam anotação de retorno, as outras não; (3)
      `Field(..., min_length=1)` com Ellipsis em `schemas/chat.py`. Nada quebrado, é alinhamento de
      estilo — fazer num PR só

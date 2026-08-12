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
- [x] Comando `/exit` e `Ctrl+C` encerrando a sessão via `chat.service.encerrar_sessao`
- [x] Bootstrap de usuário/sessão extraído pra `chat/service.py:iniciar_sessao()` — antes
      duplicado em `interfaces/terminal/app.py`, agora reaproveitado por terminal e TUI

## Testes — suíte iniciada, só funções puras por enquanto

Pasta `tests/` criada espelhando a estrutura de `tools/` (package by feature, mesmo corte usado no
resto do repo) — `chat/`, `agents/`, `graph/` ainda não têm testes (ver bullet abaixo).

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
      via `config/docker.py`) antes de crescer demais, ou manter achatado enquanto a suíte for pequena
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

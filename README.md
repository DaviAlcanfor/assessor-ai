<div align="center">

```
 █████╗ ███████╗███████╗███████╗███████╗███████╗ ██████╗ ██████╗    █████╗ ██╗
██╔══██╗██╔════╝██╔════╝██╔════╝██╔════╝██╔════╝██╔═══██╗██╔══██╗  ██╔══██╗██║
███████║███████╗███████╗█████╗  ███████╗███████╗██║   ██║██████╔╝  ███████║██║
██╔══██║╚════██║╚════██║██╔══╝  ╚════██║╚════██║██║   ██║██╔══██╗  ██╔══██║██║
██║  ██║███████║███████║███████╗███████║███████║╚██████╔╝██║  ██║  ██║  ██║██║
╚═╝  ╚═╝╚══════╝╚══════╝╚══════╝╚══════╝╚══════╝ ╚═════╝ ╚═╝  ╚═╝  ╚═╝  ╚═╝╚═╝
```

Assistente pessoal de **finanças e agenda** construído com LangChain + LangGraph.  
O sistema usa uma arquitetura multi-agente onde cada agente tem uma responsabilidade bem definida:  
classificar a intenção, processar o domínio correto e formatar a resposta final para o usuário.

![Python](https://img.shields.io/badge/Python-3.13+-3776AB?style=flat&logo=python&logoColor=white)
![LangChain](https://img.shields.io/badge/LangChain-1.2-1C3C3C?style=flat&logo=langchain&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-1.1-FF6B35?style=flat)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-psycopg2-336791?style=flat&logo=postgresql&logoColor=white)
![MongoDB](https://img.shields.io/badge/MongoDB-pymongo-47A248?style=flat&logo=mongodb&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-pyredis-FF4438?style=flat&logo=redis&logoColor=white)
![Qdrant](https://img.shields.io/badge/Qdrant-qdrant--client-DC244C?style=flat&logo=qdrant&logoColor=white)

</div>

---

## O que o Assessor.AI faz

O Assessor.AI atua como um parceiro pessoal que responde perguntas e executa ações em dois domínios:

**Finanças pessoais**
- Registra, consulta e atualiza transações (gastos, receitas, transferências)
- Calcula saldo total e saldo por dia
- Classifica transações por categoria (comida, transporte, lazer, saúde, etc.)
- Gera diagnósticos e recomendações financeiras com base nos dados reais do banco

**Agenda e compromissos**
- Cria, consulta e atualiza eventos
- Consulta eventos do dia
- Gerencia localização, horários e observações de cada evento

Para tudo fora desses dois escopos (small talk, saudações, perguntas fora de área), o próprio roteador responde diretamente ao usuário.

---

## Diagrama de agentes

```mermaid
flowchart LR
    U(["Usuário"])
    GE["Guardrail Entrada"]
    R["Router"]
    F["Financeiro"]
    A["Agenda"]
    FAQ["FAQ"]
    O["Orquestrador"]
    GS["Guardrail Saída"]
    E(["Fim"])

    U --> GE
    GE -->|"bloqueado"| E
    GE -->|"aprovado"| R
    R -->|"ROUTE=financeiro"| F
    R -->|"ROUTE=agenda"| A
    R -->|"ROUTE=faq"| FAQ
    R -->|"fora de escopo"| E
    F --> O
    A --> O
    O --> GS
    FAQ --> GS
    GS --> E
```

---

## Estrutura do projeto

```
assessor-ai/
├── main.py                          # Dispatcher — `python main.py tui|api`
├── pyproject.toml                   # Dependências do projeto
│
├── src/assessor_ai/
│   ├── api/                         # Camada HTTP (FastAPI)
│   │   ├── app.py                   # App FastAPI — routers, handlers de erro, middleware, rotas A2A
│   │   ├── lifespan.py              # Compila grafo + checkpointer no startup; dispose no shutdown
│   │   ├── exception_handlers.py    # Erros de domínio -> status HTTP + ErrorResponse{detail, code}
│   │   ├── auth.py                  # get_current_user via X-API-Key; verify_signup_secret
│   │   ├── gen_key.py               # generate_api_key
│   │   └── routes/                  # chats.py, health.py, keys.py, users.py
│   │
│   ├── services/                    # Casos de uso — não conhecem HTTP
│   │   ├── chat_service.py          # create_chat, send_message, get_history, validar_ownership, encerrar_sessao
│   │   ├── runner.py                # Invoca fluxo_agentes (graph/builder.py), propaga tags/metadata pro LangSmith
│   │   └── exceptions.py            # ChatNaoEncontrado, ChatDeOutroUsuario, LimiteDeMensagensExcedido, FalhaNoAgente
│   │
│   ├── repositories/
│   │   └── chat_repository.py       # Fachada sobre tools/chats, tools/usuarios e core/cache
│   │
│   ├── schemas/                     # Contratos de dados
│   │   ├── models.py                # ChatMessage, Role — contrato interno, independente de Mongo/tool
│   │   ├── chat.py                  # MessageCreate, ChatSummary, ChatMessageResponse (HTTP)
│   │   ├── errors.py                # ErrorResponse
│   │   └── health.py  key.py  user.py
│   │
│   ├── tui/                         # Interface Textual
│   │   ├── app.py                   # AssessorTUI — tela de chat
│   │   ├── display.py               # Bubble (Rich Panel), MessageRow, Pensando (LoadingIndicator)
│   │   └── app.tcss                 # Stylesheet do Textual
│   │
│   ├── a2a/                         # Protocolo A2A (JSON-RPC), montado no mesmo app FastAPI
│   │   ├── main.py                  # montar_rotas(app) — agent card + endpoint JSON-RPC em /a2a
│   │   └── agents/
│   │       ├── card.py              # AgentCard (nome, versão, interface, skills)
│   │       ├── capabilites.py       # AgentSkill(s) expostas no card
│   │       └── interface.py         # AssessorAgentExecutor — ponte pro services/chat_service.py
│   │
│   ├── core/                        # Infra transversal — sem dependência de camada
│   │   ├── config.py                # Env vars via pydantic-settings; credenciais em SecretStr
│   │   ├── models.py                # PROVIDER_MAP, BUILDERS, Model Enum
│   │   ├── logging.py               # ColorFormatter, get_logger e o decorator log_tool
│   │   ├── privacy.py               # Regex de PII + anonimizar_entrada (guardrail, logs e persistência)
│   │   ├── cache.py                 # buscar/salvar/invalidar_perfil_cache — cache do perfil (TTL 1h)
│   │   ├── limiter.py               # slowapi por IP + can_send_message (cota por user_id no Redis)
│   │   ├── middleware.py            # SecurityConfig do fastapi-guard
│   │   └── prompts/                 # Prompts de cada agente — .md puro + um loader
│   │       ├── loader.py            # load_prompt/load_sections, persona e contexto do turno
│   │       ├── router.md            # PAPEL + SHOTS do roteador
│   │       ├── financeiro.md        # idem financeiro (frontmatter liga obrigatoriedade de tools)
│   │       ├── agenda.md            # idem agenda (frontmatter liga obrigatoriedade de tools)
│   │       ├── orquestrador.md      # idem orquestrador
│   │       ├── faq.md               # idem FAQ
│   │       ├── guardrail.md         # templates CLASSIFICADOR e COMPLIANCE
│   │       └── resumidor.md         # templates RESUMO e PERFIL
│   │
│   ├── agents/nodes/                # Funções de nó do grafo LangGraph
│   │   ├── names.py                 # NodeName StrEnum
│   │   ├── router.py                # no_roteador
│   │   ├── financeiro.py            # no_financeiro
│   │   ├── agenda.py                # no_agenda
│   │   ├── faq.py                   # no_faq
│   │   ├── orquestrador.py          # no_orquestrador
│   │   └── guardrail/
│   │       ├── entrada.py           # no_guardrail_entrada — anonimização PII + classificação LLM
│   │       ├── saida.py             # no_guardrail_saida — redação PII + revisão compliance
│   │       └── schemas.py           # ResultadoGuardrail, Categoria, padrões de injeção e keywords
│   │
│   ├── graph/
│   │   ├── state.py                 # Estado e Route StrEnum
│   │   ├── llm.py                   # build_llm e instâncias de LLM
│   │   ├── agents.py                # Agentes compilados (router_app, financeiro_app, etc.)
│   │   └── builder.py               # Construção e compilação do grafo LangGraph
│   │
│   └── tools/                        # Uma pasta por feature; conexões em tools/infra/
│       ├── infra/                    # O que é compartilhado entre features
│       │   ├── postgres.py           # PostgresConn (engine + pool do checkpointer, lazy), Base,
│       │   │                         #   @transacional, PostgresRepo, ContextVar current_user_id
│       │   ├── mongo.py              # MongoConn + MongoRepo (resolve a collection da subclasse)
│       │   ├── redis.py              # RedisConn
│       │   └── qdrant.py             # QdrantConn + modelo de embedding
│       ├── financeiro/
│       │   ├── models.py             # Transaction, Category, TransactionType, PaymentType
│       │   ├── schemas.py            # Schemas Pydantic dos argumentos das tools
│       │   └── repo.py               # FinanceiroRepo — 5 tools: add/query/update_transaction, total/daily_balance
│       ├── agenda/
│       │   ├── models.py             # Event
│       │   ├── schemas.py            # Schemas Pydantic dos argumentos das tools
│       │   └── repo.py               # AgendaRepo — 4 tools: add_event, query_events, query_daily_events, update_event
│       ├── faq/
│       │   ├── schemas.py            # FaqRetrieverArgs, SearchResponse
│       │   ├── repo.py               # FaqRepo — tool faq_retriever (busca semântica no Qdrant)
│       │   └── ingest.py             # Script (`python -m ...faq.ingest`) que indexa o PDF de FAQ
│       ├── chats/                    # Interno (não é tool do LLM)
│       │   ├── schemas.py            # ChatDocument, Role, Mensagem
│       │   ├── helpers.py            # gerar_resumo, gerar_perfil
│       │   └── repo.py               # ChatsRepo — criar, buscar, atualizar_mensagens, encerrar_sessao
│       ├── usuarios/                 # Interno — única feature que cruza os três bancos
│       │   ├── models.py             # User (linha de FK no Postgres)
│       │   ├── schemas.py            # UserDocument + chaves/TTL da API key
│       │   └── repo.py               # UsuariosRepo — cadastro/perfil (Mongo), garantir_usuario (Mongo+PG), API key (Redis)
│       └── response.py               # Classe Response para padronizar retornos
│
├── alembic/                         # Migrations versionadas do schema PostgreSQL
│
└── data/
    └── documents/                   # PDFs para RAG
        └── FAQ_assessor_v1.1.pdf
```

---

## Fluxo dos agentes

```
Usuário
│
▼
[Guardrail Entrada]  ──── bloqueado ───► encerra (sem persistir no histórico)
│  detecta prompt injection e acesso a dados internos (determinístico)
│  classifica a mensagem via LLM (APROVADO | OFENSIVO | PERIGOSO | ILICITO | ...)
│  anonimiza PII antes de passar adiante
│
▼
[Router]  ──── small talk / fora de escopo ───► responde diretamente ao usuário
│
│ ROUTE=financeiro|agenda|faq
▼
[Especialista]  (Financeiro, Agenda ou FAQ)
│  consulta/escreve no banco via tools
│  popula resposta_especialista no estado
▼
[Orquestrador]  (apenas Financeiro e Agenda)
│  recebe o JSON do especialista + histórico da conversa
│  formata a resposta em linguagem natural
▼
[Guardrail Saída]
│  redige PII remanescente
│  revisa compliance (CVM/ANBIMA): remove garantias de rentabilidade e recomendações de ativos sem disclaimer
▼
Usuário
```

### Agentes em detalhe

| Agente | Modelo | Responsabilidade |
|---|---|---|
| **Guardrail Entrada** | `gemini-2.5-flash` (temp 0.0) | Bloqueia mensagens indevidas e anonimiza PII |
| **Router** | `llama-3.3-70b-versatile` (temp 0.0) | Classifica a intenção e emite `ROUTE=financeiro\|agenda\|faq`, ou responde diretamente |
| **Financeiro** | `gemini-2.5-flash` + fallback `llama-3.3-70b` | Interpreta a pergunta financeira e chama as tools do banco |
| **Agenda** | `gemini-2.5-flash` + fallback `llama-3.3-70b` | Interpreta perguntas de agenda e chama as tools de eventos |
| **FAQ** | `llama-3.3-70b-versatile` (temp 0.0) | Consulta o PDF via RAG e responde dúvidas sobre o sistema |
| **Orquestrador** | `llama-3.3-70b-versatile` (temp 0.0) | Formata a resposta do especialista em linguagem natural |
| **Guardrail Saída** | `llama-3.3-70b-versatile` (temp 0.0) | Revisa compliance e redige PII na resposta final |

---

## Guardrails

### Entrada

O guardrail de entrada executa verificações em ordem de custo crescente:

1. **Detecção determinística** — regex para prompt injection e keywords de acesso a dados internos
2. **Anonimização de PII** — substitui CPF, CNPJ, número de conta, cartão, e-mail e telefone por tokens antes de passar ao LLM
3. **Classificação LLM** — categoriza a mensagem em `APROVADO`, `OFENSIVO`, `PERIGOSO`, `ILICITO`, `POLITICO` ou `INDICACAO_INVEST`

Mensagens bloqueadas não são persistidas no histórico.

### Saída

O guardrail de saída nunca bloqueia — apenas revisa:

1. **Redação de PII** — remove dados pessoais remanescentes da resposta (CPF, CNPJ, número de conta e cartão)
2. **Compliance CVM/ANBIMA** — corrige afirmações que garantam rentabilidade futura ou recomendem ativos sem disclaimer de risco

---

## Tools

### Financeiro (PostgreSQL)

| Tool | Descrição |
|---|---|
| `add_transaction` | Insere uma transação (amount, tipo, categoria, método de pagamento) |
| `query_transactions` | Consulta transações com filtros por data, tipo e texto |
| `update_transaction` | Atualiza transação por ID ou por busca de texto + data |
| `total_balance` | Retorna saldo total (INCOME − EXPENSES) |
| `daily_balance` | Retorna saldo de um dia específico |

Tipos de transação: `INCOME` (1), `EXPENSES` (2), `TRANSFER` (3).  
Categorias: `comida`, `besteira`, `estudo`, `férias`, `transporte`, `moradia`, `saúde`, `lazer`, `contas`, `investimento`, `presente`, `outros`.

### Agenda (PostgreSQL)

| Tool | Descrição |
|---|---|
| `add_event` | Insere um evento (título, horário, local, observações) |
| `query_events` | Consulta eventos com filtros por período e título |
| `query_daily_events` | Retorna todos os eventos de um dia específico |
| `update_event` | Atualiza evento por ID ou por busca de texto + data |

### FAQ (RAG)

| Tool | Descrição |
|---|---|
| `faq_retriever` | Busca semântica no PDF de FAQ via Qdrant + Gemini Embeddings (`tools/faq/`) |

Indexação: `python -m assessor_ai.tools.qdrant.faq.ingest` (script separado da tool, roda sob demanda).

---

## Persistência

| Camada | Tecnologia | Responsabilidade |
|---|---|---|
| **Transações e eventos** | PostgreSQL (Docker) | Dados financeiros e de agenda do usuário |
| **Histórico de conversa** | MongoDB | Mensagens por sessão (últimas 5 por consulta) |
| **Checkpointing de grafo** | LangGraph MongoDBSaver | Estado interno do grafo entre turnos, persistido no Mongo (`graph_checkpoints`/`graph_checkpoint_writes`) |
| **Cache de perfil, rate limit, API keys** | Redis | Cache do `perfil_usuario` (TTL 1h), limite de mensagens por `user_id` na janela de 60s, hash de API keys da API |

O MongoDB armazena `users` (cadastro e perfil comportamental), `chats` (histórico de mensagens por sessão) e `graph_checkpoints`/`graph_checkpoint_writes` (estado do LangGraph, via `MongoDBSaver`). O histórico de mensagens é limitado via projeção `$slice: -5` para evitar contextos longos demais.

O campo `perfil_usuario` — gerado a partir do histórico acumulado e armazenado em `users` — é carregado no estado do grafo antes de cada invocação, servindo como contexto cross-session do usuário. É lido do Redis primeiro (`core/cache.py`); só cai no Mongo em cache miss, e o cache é invalidado ao encerrar a sessão (quando o perfil pode ter sido atualizado a partir do resumo).

O RAG do FAQ roda sobre o Qdrant (`tools/faq/`) — substituiu o índice FAISS local.

---

## Configuração

### Variáveis de ambiente

```env
GEMINI_API_KEY=...
GROQ_API_KEY=...
POSTGRES_URL=postgresql://usuario:senha@host:5432/banco
MONGO_URL=mongodb://usuario:senha@host:27017/
MONGO_COLLECTION_NAME=assessor
REDIS_URL=redis://host:6379/0
QDRANT_URL=http://host:6333
QDRANT_COLLECTION_NAME=faq
SIGNUP_SECRET=...
LANGSMITH_TRACING=false
LANGSMITH_API_KEY=...
LANGSMITH_PROJECT=assessor-ai
API_KEY_AUTH_ENABLED=true
```

Ver [.env.example](.env.example) para a referência completa (inclui `QDRANT_API_KEY` opcional, usada só em instâncias cloud do Qdrant). `SIGNUP_SECRET` é obrigatório — sem ele `Settings()` falha ao importar; é o valor exigido no header `X-Signup-Secret` do `POST /v1/keys`. `LANGSMITH_*` é opcional — só ativa tracing/observabilidade do grafo se `LANGSMITH_TRACING=true` (ver seção [Observabilidade](#observabilidade) abaixo). `API_KEY_AUTH_ENABLED` é opcional (default `true`) — com `false`, `/v1/chats` para de exigir `X-API-Key` e passa a reaproveitar/criar um usuário padrão a cada request (`chat_service.obter_usuario_padrao`, mesmo bootstrap do terminal/TUI); é um desligamento temporário pro estágio atual do projeto, não uma remoção — a chave de rota, `api/auth.py:get_current_user`, continua existindo e testada (ver `TODO.md`).
A2A_BASE_URL=http://localhost:8000
```

Ver [.env.example](.env.example) para a referência completa (inclui `QDRANT_API_KEY` opcional, usada só em instâncias cloud do Qdrant). `SIGNUP_SECRET` é obrigatório — sem ele `Settings()` falha ao importar; é o valor exigido no header `X-Signup-Secret` do `POST /v1/keys`. `LANGSMITH_*` é opcional — só ativa tracing/observabilidade do grafo se `LANGSMITH_TRACING=true` (ver seção [Observabilidade](#observabilidade) abaixo). `A2A_BASE_URL` é opcional (default já cobre execução local) — só muda a URL declarada no `AgentCard` do A2A (ver seção [A2A](#a2a) acima).

### Instalação

```bash
uv venv
uv sync
```

### Execução

```bash
python main.py tui        # interface Textual
python main.py api        # sobe a API FastAPI via uvicorn em 0.0.0.0:8000
```

Postgres, Mongo, Redis e Qdrant são serviços em nuvem — não há infra local pra subir. Na TUI,
digite `/exit` (ou `Ctrl+C`) pra encerrar a sessão.

Também dá pra rodar via `justfile`: `just venv` (cria `.venv`), `just run [modo]` (default `tui`)
e `just dev [modo]` (mesma coisa, injetando env vars via `infisical run --`).

### A2A

`python main.py api` também expõe o protocolo [A2A](https://a2a-protocol.org/) (agent-to-agent),
montado no mesmo app FastAPI:

- `GET /.well-known/agent-card.json` — [`AgentCard`](src/assessor_ai/a2a/agents/card.py) com nome,
  versão e as skills expostas ([`capabilites.py`](src/assessor_ai/a2a/agents/capabilites.py)):
  - `moneysaving` — registra e consulta transações, saldo total/diário e gastos por categoria e período
  - `agenda` — cria, consulta e atualiza compromissos do calendário
  - `faq` — perguntas sobre o que o assistente faz e como usá-lo

  As skills são só metadado de discovery; `POST /a2a` roteia toda mensagem pelo grafo completo
  (o router decide o domínio), independente de qual skill o cliente achou no card.
- `POST /a2a` — endpoint JSON-RPC (método `SendMessage`) que processa a mensagem via
  [`AssessorAgentExecutor`](src/assessor_ai/a2a/agents/interface.py), a mesma camada `services/chat_service.py`
  usada por terminal/TUI/API. Cada `context_id` do protocolo vira uma sessão/usuário do Assessor —
  na primeira mensagem, ou sem `context_id`.

Primeira versão, sem tarefas assíncronas (`streaming`/`push_notifications` desligados no
`AgentCard`) nem autenticação — a rota está aberta de propósito, porque a auth por API key
atrapalha o caso de uso A2A entre agentes (ver `TODO.md`).

### Migrations (Alembic)

Schema do PostgreSQL versionado em `alembic/versions/`. Com o container do Postgres no ar
(`POSTGRES_URL` configurado):

```bash
uv run alembic upgrade head
```

O acesso a dados usa SQLAlchemy ORM (`tools/{financeiro,agenda,usuarios}/models.py`), então `--autogenerate` funciona
normalmente a partir daqui:

```bash
uv run alembic revision --autogenerate -m "..."
```

Sempre revise o diff gerado antes de aplicar — e rode `--autogenerate` sem alterações pendentes de
vez em quando pra garantir que os models continuam batendo exatamente com o schema real (diff vazio).

---

## Observabilidade

Tracing dos agentes via [LangSmith](https://smith.langchain.com/) — opcional, desligado por padrão
(`LANGSMITH_TRACING=false`). Quando ligado, `graph.invoke()` (`services/runner.py:executar`) é
rastreado automaticamente pelo LangChain/LangGraph, incluindo cada nó (guardrail, router,
financeiro, agenda, faq, orquestrador) e cada chamada de LLM — sem precisar instrumentar nada à
mão. `runner.py` também passa `tags=["chat"]` e `metadata={"user_id", "session_id"}` no `config`
do `invoke()`, propagados automaticamente pra todo run filho, permitindo filtrar/auditar traces por
usuário ou sessão no painel do LangSmith.

Pontos de I/O que o LangChain não rastreia sozinho (`repositories/chat_repository.py:buscar_perfil`,
`buscar_historico`, `salvar_mensagens`) usam `@traceable` manual, com `process_inputs`/
`process_outputs` redigindo PII (reaproveitando `anonimizar_entrada` do guardrail) antes de subir
pro LangSmith Cloud.

**Limitação conhecida:** essa redação cobre só os pontos com `@traceable` manual — o run raiz do
LangGraph e o próprio nó de guardrail de entrada (auto-rastreados) ainda logam a mensagem crua do
usuário como input, já que a anonimização só acontece no *output* desse nó. Ver TODO.md pra mais
contexto antes de ligar tracing em produção com dado real.

---

## Dependências principais

- [LangChain](https://github.com/langchain-ai/langchain) — framework de agentes e tools
- [LangGraph](https://github.com/langchain-ai/langgraph) — orquestração stateful e checkpointing
- [LangSmith](https://smith.langchain.com/) — tracing/observabilidade opcional do grafo (ver [Observabilidade](#observabilidade))
- [FastAPI](https://fastapi.tiangolo.com/) — API HTTP (`api/`), com [slowapi](https://github.com/laurentS/slowapi) pro rate limit por IP
- [a2a-sdk](https://github.com/a2aproject/a2a-python) — protocolo A2A (`a2a/`), agent card + JSON-RPC montados no mesmo app FastAPI
- [Textual](https://github.com/Textualize/textual) — TUI (`tui/`)
- [SQLAlchemy](https://www.sqlalchemy.org/) — ORM sobre o PostgreSQL (`tools/{financeiro,agenda,usuarios}/models.py`), com `psycopg2` como driver
- [Alembic](https://alembic.sqlalchemy.org/) — migrations versionadas do schema PostgreSQL
- [pymongo](https://pymongo.readthedocs.io/) — driver MongoDB para histórico de conversa
- [redis-py](https://github.com/redis/redis-py) — cache de perfil, rate limit de mensagens e API keys (`tools/infra/redis.py`)
- [qdrant-client](https://github.com/qdrant/qdrant-client) — busca vetorial para RAG do FAQ (`tools/faq/`)
- [Rich](https://github.com/Textualize/rich) + [pyfiglet](https://github.com/pwaller/pyfiglet) — interface de terminal e arte ASCII da TUI
- [Pydantic](https://docs.pydantic.dev/) — validação de schemas das tools
- `langchain-anthropic`, `langchain-google-genai`, `langchain-groq` — integrações com providers

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
├── app/                             # O pacote (`from app.x import y`)
│   ├── settings/                    # pydantic-settings por grupo: api, api_keys, database, llm, mercado, observability
│   │
│   ├── domain/                      # Tipos neutros, sem I/O (qualquer camada pode importar)
│   │   ├── errors.py                # DomainError (status_code, code, public_message) e as exceções de domínio
│   │   ├── types.py                 # UserID, ChatID, APIKey... (NewType + Field p/ OpenAPI)
│   │   ├── identifiers.py           # novo_chat_id, novo_user_id
│   │   ├── privacy.py               # Regex de PII + anonimizar_entrada
│   │   └── models/                  # chat.py (ChatMessage, Role), chat_store.py, usuario.py, perfil.py, financeiro.py
│   │
│   ├── schemas/                     # Contratos HTTP (chat, perfil, auth, key, user, health, errors)
│   │
│   ├── infra/                       # Conexões e clientes externos, um pacote por sistema
│   │   ├── base.py                  # Conector[T]: contrato mínimo das conexões
│   │   ├── context.py               # session_context(user_id) / current_user_id — escopo do usuário do turno
│   │   ├── postgres/                # PostgresConn, PostgresRepo, @transacional, models/ (ORM)
│   │   ├── mongo/  qdrant/          # MongoConn + MongoRepo; QdrantConn + embeddings
│   │   ├── redis/                   # RedisConn, cache do perfil, rate_limit (por usuário), session (web)
│   │   ├── llm/                     # registry + builder dos providers; jev/ = Decisions API do Vercel AI Gateway
│   │   ├── mercado/                 # AwesomeAPI e Banco Central: MercadoClient, CacheTTL, schemas
│   │   └── logging/                 # Logging (get_logger, log_tool, log_classe), request_id
│   │
│   ├── repositories/                # Persistência crua e síncrona, um módulo por agregado
│   │   └── financeiro_, agenda_, categoria_, usuario_, chat_, perfil_, faq_repository.py
│   │
│   ├── services/                    # Casos de uso e regra (async) — os ÚNICOS que importam repositories
│   │   ├── chat_service.py          # create_chat, send_message(_stream), get_history, validar_ownership
│   │   ├── runner.py                # Invoca o grafo via ainvoke/astream_events; abre o session_context
│   │   ├── financeiro_service.py    # agenda_service.py, mercado_service.py, perfil_service.py, faq_service.py
│   │   └── user_, auth_, categoria_, memoria_, health_service.py
│   │
│   ├── graph/                       # O que o `runner` executa
│   │   ├── nodes/                   # no_roteador, no_financeiro, no_agenda, no_faq, no_orquestrador, no_juiz
│   │   ├── guardrail/               # entrada.py, saida.py, schemas.py (categorias, respostas de bloqueio)
│   │   ├── prompts/                 # Prompts .md + loader.py (load_prompt/load_sections)
│   │   ├── tools/                   # Uma pasta por domínio: schemas.py + tools.py (ToolSet fina)
│   │   │   ├── base.py              # ToolSet: Response.catch + log por método + as_tools() automático
│   │   │   ├── response.py          # ResponseStatus, ToolResponse e classe Response
│   │   │   └── financeiro/  agenda/  mercado/  perfil/  faq/
│   │   ├── agents.py                # router_app, financeiro_app, agenda_app, faq_app, orquestrador_app
│   │   ├── state.py  names.py       # Estado, Route; NodeName e constantes dos nós
│   │   └── llm.py  builder.py       # Cadeias de LLM com reserva; construção do grafo LangGraph
│   │
│   ├── telemetry/                   # metrics.py (medir_node, medir_externo), metrics_callback.py
│   │
│   ├── api/                         # Portas de entrada HTTP
│   │   ├── app.py  lifespan.py  limiter.py
│   │   ├── auth/                    # dependencies.py (X-API-Key, sessão, CSRF), keys.py
│   │   ├── middleware/              # http_metrics, request_id, security (fastapi-guard)
│   │   ├── errors/                  # handlers.py: DomainError -> status HTTP + ErrorResponse
│   │   ├── routes/                  # health.py e v1/ (auth, categories, chats, keys, perfil, users)
│   │   ├── a2a/                     # Protocolo A2A: routes, card, skills, executor, sessions
│   │   └── mcp/                     # Servidor MCP: server, adapter, auth (IdentidadeMCP), resources, annotations
│   │
│   └── tui/                         # Interface Textual (app.py, display.py, app.tcss)
│
├── tests/                           # Espelha app/ — mais test_arquitetura.py (regras de camada)
├── alembic/                         # Migrations versionadas do schema PostgreSQL
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
[Juiz]  (apenas Financeiro e Agenda)
│  confere a frase contra a fala do usuário e o que as tools receberam e devolveram
│  aprovou: a transação do turno pode ser confirmada · recusou: a frase vira a segura e as escritas do turno são desfeitas
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
| **Guardrail Entrada** | JeV (com gateway) → `gemini-2.5-flash` (temp 0.0) | Bloqueia mensagens indevidas e anonimiza PII |
| **Router** | JeV (com gateway) → `openai/gpt-oss-120b` (temp 0.0) | JeV escolhe `financeiro\|agenda\|faq`; se escolher `nenhum`, o LLM emite `ROUTE=` ou responde diretamente |
| **Financeiro** | `gemini-2.5-flash` → `openai/gpt-oss-120b` → GPT-6 Luna | Interpreta a pergunta financeira e chama as tools do banco |
| **Agenda** | `gemini-2.5-flash` → `openai/gpt-oss-120b` → GPT-6 Luna | Interpreta perguntas de agenda e chama as tools de eventos |
| **FAQ** | `openai/gpt-oss-120b` (temp 0.0) | Consulta o PDF via RAG e responde dúvidas sobre o sistema |
| **Orquestrador** | `openai/gpt-oss-120b` (temp 0.0) | Formata a resposta do especialista em linguagem natural |
| **Juiz** | JeV (sem LLM de reserva) | Aprova ou recusa o turno; só com aprovação as escritas no Postgres são confirmadas |
| **Guardrail Saída** | `openai/gpt-oss-120b` (temp 0.0) | Revisa compliance e redige PII na resposta final |

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

### Juiz e escritas no Postgres

As tools que gravam (`add_transaction`, `update_transaction`, `add_event`, `update_event`) não confirmam
nada sozinhas durante o chat: o runner abre uma transação por turno (`infra/postgres/transacao_do_turno.py`),
as tools gravam dentro dela, e o commit só acontece no fim do grafo, se o juiz aprovou. Recusa, juiz fora do ar,
exceção ou queda do processo desfazem o turno. Fora do chat (MCP) o commit continua imediato. A decisão e as
alternativas descartadas estão no [decisao_tecnica.md](decisao_tecnica.md).

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

### Mercado (cotação e indicadores)

Tools do agente financeiro (`graph/tools/mercado/`, regra em `services/mercado_service.py`), sobre APIs públicas sem chave: AwesomeAPI e
Banco Central (`infra/mercado/`). Cache em memória (1 min na cotação atual, 1 h no resto).

| Tool | Descrição |
|---|---|
| `cotacao_atual` | Compra, venda, variação do dia, máxima e mínima de USD, EUR, BTC... contra o real |
| `cotacao_historica` | Cotação diária num período, com mínima, máxima, média e variação |
| `ptax_dolar` | Fechamento oficial do dólar (PTAX do Banco Central); em fim de semana devolve o último fechamento |
| `converter_moeda` | Converte um valor entre duas moedas, pela cotação de compra |
| `indicador_economico` | Meta Selic, CDI, IPCA mensal e IPCA acumulado em 12 meses |
| `simular_investimento` | Juros compostos com aportes, a uma taxa anual ou a um % do CDI/Selic (bruto, sem IR/IOF, com aviso de que não é garantia) |

### FAQ (RAG)

| Tool | Descrição |
|---|---|
| `faq_retriever` | Busca semântica no PDF de FAQ via Qdrant + Gemini Embeddings (`graph/tools/faq/`, `repositories/faq_repository.py`) |

Indexação: `python -m assessor_ai.graph.tools.faq.ingest` (script separado da tool, roda sob demanda).

---

## Persistência

| Camada | Tecnologia | Responsabilidade |
|---|---|---|
| **Transações e eventos** | PostgreSQL | Dados financeiros e de agenda do usuário |
| **Histórico de conversa** | MongoDB | Mensagens por sessão (últimas 5 por consulta) |
| **Checkpointing de grafo** | LangGraph AsyncPostgresSaver | Estado interno do grafo entre turnos, persistido no PostgreSQL |
| **Cache de perfil, rate limit, API keys** | Redis | Cache do `perfil_usuario` (TTL 1h), limite de mensagens por `user_id` na janela de 60s, hash de API keys da API |

O MongoDB armazena `users` (cadastro e perfil comportamental) e `chats` (histórico de mensagens por sessão). O histórico de mensagens é limitado via projeção `$slice: -5` para evitar contextos longos demais.

O campo `perfil_usuario` — gerado a partir do histórico acumulado e armazenado em `users` — é carregado no estado do grafo antes de cada invocação, servindo como contexto cross-session do usuário. É lido do Redis primeiro (`infra/cache.py`); só cai no Mongo em cache miss, e o cache é invalidado ao encerrar a sessão (quando o perfil pode ter sido atualizado a partir do resumo).

O RAG do FAQ roda sobre o Qdrant (`graph/tools/faq/`, `repositories/faq_repository.py`) — substituiu o índice FAISS local.

---

## Configuração

### Variáveis de ambiente

O `settings/` agrupa a configuração e o grupo vira prefixo com `__` no `.env`
(`DATABASE__POSTGRES_URL`, `LLM__GROQ__API_KEY`). Variável com nome errado **não dá erro**
(`extra="ignore"`): ela só some — confira com `python -c "from assessor_ai.settings import settings; print(settings)"`.

```env
LLM__GEMINI__API_KEY=...
LLM__GROQ__API_KEY=...
LLM__GATEWAY__API_KEY=...      # opcional — Vercel AI Gateway: GPT-6 Luna nas cadeias; JeV no guardrail e roteador
DATABASE__POSTGRES_URL=postgresql://usuario:senha@host:5432/banco
DATABASE__MONGO_URL=mongodb://usuario:senha@host:27017/
DATABASE__MONGO_COLLECTION_NAME=assessor
DATABASE__REDIS_URL=redis://host:6379/0
DATABASE__QDRANT_URL=http://host:6333
DATABASE__QDRANT_COLLECTION_NAME=faq
API_KEYS__SIGNUP_SECRET=...
OBSERVABILITY__LANGSMITH_TRACING=false
OBSERVABILITY__LANGSMITH_API_KEY=...
OBSERVABILITY__LANGSMITH_PROJECT=assessor-ai
API__KEY_AUTH_ENABLED=true
API__A2A_BASE_URL=http://localhost:8000
```

Ver [.env.example](.env.example) para a referência completa (inclui `DATABASE__QDRANT_API_KEY`, usada só em instâncias cloud do Qdrant). `API_KEYS__SIGNUP_SECRET` é obrigatório — sem ele `Settings()` falha ao importar; é o valor exigido no header `X-Signup-Secret` do `POST /v1/keys`. `OBSERVABILITY__LANGSMITH_*` é opcional — só ativa tracing se `OBSERVABILITY__LANGSMITH_TRACING=true` (ver seção [Observabilidade](#observabilidade)). `API__KEY_AUTH_ENABLED` é opcional (default `true`) — com `false`, `/v1/chats` para de exigir `X-API-Key` e passa a reaproveitar/criar um usuário padrão a cada request (`chat_service.obter_usuario_padrao`, mesmo bootstrap do terminal/TUI); é um desligamento temporário pro estágio atual do projeto (ver `TODO.md`). `API__A2A_BASE_URL` só muda a URL declarada no `AgentCard` do A2A (ver seção [A2A](#a2a)). Com `ENVIRONMENT=production` o `Settings` recusa auth desligada, cookie sem `Secure` e CORS `*`.

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

- `GET /.well-known/agent-card.json` — [`AgentCard`](app/api/a2a/card.py) com nome,
  versão e as skills expostas ([`capabilites.py`](app/api/a2a/skills.py)):
  - `moneysaving` — registra e consulta transações, saldo total/diário e gastos por categoria e período
  - `agenda` — cria, consulta e atualiza compromissos do calendário
  - `faq` — perguntas sobre o que o assistente faz e como usá-lo

  As skills são só metadado de discovery; `POST /a2a` roteia toda mensagem pelo grafo completo
  (o router decide o domínio), independente de qual skill o cliente achou no card.
- `POST /a2a` — endpoint JSON-RPC (método `SendMessage`) que processa a mensagem via
  [`AssessorAgentExecutor`](app/api/a2a/executor.py), a mesma camada `services/chat_service.py`
  usada por terminal/TUI/API. Cada `context_id` do protocolo vira uma sessão/usuário do Assessor —
  na primeira mensagem, ou sem `context_id`.

Primeira versão, sem tarefas assíncronas (`streaming`/`push_notifications` desligados no
`AgentCard`) nem autenticação — a rota está aberta de propósito, porque a auth por API key
atrapalha o caso de uso A2A entre agentes (ver `TODO.md`).

### MCP

`python main.py api` também monta um servidor [MCP](https://modelcontextprotocol.io/) em `/mcp` (HTTP
streamable, stateless), pra clientes como Claude Desktop ou IDEs usarem as mesmas tools dos agentes —
transações e saldo, agenda e dados de mercado (cotação, PTAX, Selic/CDI/IPCA, simulação) — mais o resource
`categories://all`.

- **Autenticação:** header `X-API-Key` (a mesma chave do `POST /v1/keys`). Sem chave, 401. Cada request roda
  com o usuário dono da chave (`IdentidadeMCP` abre o `session_context`); em modo dev
  (`API__KEY_AUTH_ENABLED=false`) usa o usuário padrão.
- **Hosts permitidos:** o servidor recusa (421) qualquer `Host` fora de `API__MCP_ALLOWED_HOSTS` (padrão:
  `localhost`/`127.0.0.1` com porta). Em deploy, ponha o domínio público.
- **Tools:** saem sozinhas das listas `FINANCEIRO_TOOLS`/`AGENDA_TOOLS`/`MERCADO_TOOLS`, com o schema e as
  descrições de cada `args_schema`. Detalhes e pegadinhas em `.agents/skills/mcp.md`.

## Migrations (Alembic)

Schema do PostgreSQL versionado em `alembic/versions/` (`DATABASE__POSTGRES_URL` configurado):

```bash
uv run alembic upgrade head
```

O acesso a dados usa SQLAlchemy ORM (`infra/postgres/models/`), então `--autogenerate` funciona
normalmente a partir daqui:

```bash
uv run alembic revision --autogenerate -m "..."
```

Sempre revise o diff gerado antes de aplicar — e rode `--autogenerate` sem alterações pendentes de
vez em quando pra garantir que os models continuam batendo exatamente com o schema real (diff vazio).

---

## Observabilidade

Tracing dos agentes via [LangSmith](https://smith.langchain.com/) — opcional, desligado por padrão
(`OBSERVABILITY__LANGSMITH_TRACING=false`). Quando ligado, `graph.ainvoke()` (`services/runner.py:executar`) é
rastreado automaticamente pelo LangChain/LangGraph, incluindo cada nó (guardrail, router,
financeiro, agenda, faq, orquestrador) e cada chamada de LLM — sem precisar instrumentar nada à
mão. `runner.py` também passa `tags=["chat"]` e `metadata={"user_id", "session_id"}` no `config`
do `invoke()`, propagados automaticamente pra todo run filho, permitindo filtrar/auditar traces por
usuário ou sessão no painel do LangSmith.

Pontos de I/O que o LangChain não rastreia sozinho (`services/user_service.py:buscar_perfil` e, em
`services/chat_service.py`, `buscar_historico` e `salvar_mensagens`) usam `@traceable` manual, com `process_inputs`/
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
- [SQLAlchemy](https://www.sqlalchemy.org/) — ORM sobre o PostgreSQL (`infra/postgres/models/`), com `psycopg2` como driver
- [Alembic](https://alembic.sqlalchemy.org/) — migrations versionadas do schema PostgreSQL
- [pymongo](https://pymongo.readthedocs.io/) — driver MongoDB para histórico de conversa
- [redis-py](https://github.com/redis/redis-py) — cache de perfil, rate limit de mensagens e API keys (`infra/redis.py`)
- [qdrant-client](https://github.com/qdrant/qdrant-client) — busca vetorial para RAG do FAQ (`graph/tools/faq/`, `repositories/faq_repository.py`)
- [Rich](https://github.com/Textualize/rich) + [pyfiglet](https://github.com/pwaller/pyfiglet) — interface de terminal e arte ASCII da TUI
- [Pydantic](https://docs.pydantic.dev/) — validação de schemas das tools
- `langchain-anthropic`, `langchain-google-genai`, `langchain-groq` — integrações com providers

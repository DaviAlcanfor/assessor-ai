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
├── main.py                          # Dispatcher — `python main.py terminal|tui|api`
├── pyproject.toml                   # Dependências do projeto
│
├── chat/                            # Camada de serviço compartilhada entre as interfaces
│   ├── models.py                    # ChatMessage, Role — contrato interno, independente de Mongo/tool
│   ├── repositories.py              # Acesso a tools/mongo/chats, tools/mongo/users e tools/postgres/users
│   ├── runner.py                    # Invoca fluxo_agentes (graph/builder.py) e extrai a resposta
│   └── service.py                   # create_chat, send_message, get_history, encerrar_sessao — API pública
│
├── interfaces/                      # Um pacote por forma de uso, todos consumindo chat/service.py
│   ├── terminal/
│   │   ├── app.py                   # run() — loop de input() do terminal
│   │   └── display.py               # Interface Rich + pyfiglet (exibir_titulo, exibir_usuario, ...)
│   ├── tui/
│   │   └── app.py                   # (vazio — ver TODO.md "TUI com Textual")
│   └── api/
│       └── app.py                   # (vazio — ver TODO.md "API")
│
├── agents/
│   ├── prompts/                     # Prompts de cada agente
│   │   ├── base.py                  # GenericAgent: persona, contexto temporal e montagem de shots
│   │   ├── router.py                # RouterPrompts
│   │   ├── financeiro.py            # FinanceiroPrompts
│   │   ├── agenda.py                # AgendaPrompts
│   │   ├── orquestrador.py          # OrquestradorPrompts
│   │   ├── faq.py                   # FaqPrompts
│   │   ├── guardrail.py             # GuardrailPrompts
│   │   └── resumidor.py             # ResumidorPrompt, PerfilPrompt
│   └── nodes/                       # Funções de nó do grafo LangGraph
│       ├── names.py                 # NodeName StrEnum
│       ├── router.py                # no_roteador
│       ├── financeiro.py            # no_financeiro
│       ├── agenda.py                # no_agenda
│       ├── faq.py                   # no_faq
│       ├── orquestrador.py          # no_orquestrador
│       └── guardrail/
│           ├── entrada.py           # no_guardrail_entrada — anonimização PII + classificação LLM
│           ├── saida.py             # no_guardrail_saida — redação PII + revisão compliance
│           └── schemas.py           # ResultadoGuardrail, Categoria, PII, padrões e keywords
│
├── graph/
│   ├── state.py                     # Estado e Route StrEnum
│   ├── llm.py                       # build_llm e instâncias de LLM
│   ├── agents.py                    # Agentes compilados (router_app, financeiro_app, etc.)
│   └── builder.py                   # Construção e compilação do grafo LangGraph
│
├── tools/
│   ├── postgres/
│   │   ├── models.py                # Models declarativos SQLAlchemy (User, Transaction, Event, ...)
│   │   ├── financeiro/
│   │   │   ├── schemas.py           # Schemas Pydantic das tools financeiras
│   │   │   └── core.py              # Tools: add_transaction, query_transactions, update_transaction, total_balance, daily_balance
│   │   ├── agenda/
│   │   │   ├── schemas.py           # Schemas Pydantic das tools de agenda
│   │   │   └── core.py              # Tools: add_event, query_events, query_daily_events, update_event
│   │   ├── users/
│   │   │   └── core.py              # garantir_usuario — mesmo user_id do Mongo, tabela enxuta
│   │   ├── connection.py            # Engine/Session SQLAlchemy (lazy init)
│   │   └── helpers.py               # resolve_type_id, get_category_id, local_date_filter, local_date_range_filter
│   ├── mongo/
│   │   ├── connection.py            # MongoClient lazy — conecta só na primeira operação
│   │   ├── helpers.py               # _gerar_resumo, _gerar_perfil
│   │   ├── chats/
│   │   │   ├── schemas.py           # ChatDocument, Role, Mensagem
│   │   │   └── core.py              # criar, buscar, atualizar_mensagens, inserir_resumo, encerrar_sessao
│   │   └── users/
│   │       ├── schemas.py           # UserDocument
│   │       └── core.py              # inserir, buscar, buscar_por_email, atualizar_perfil, garantir_usuario
│   ├── faq_tools.py                 # Tool de RAG sobre o PDF de FAQ (lazy init)
│   └── response.py                  # Classe Response para padronizar retornos
│
├── config/
│   ├── settings.py                  # Carrega e valida variáveis de ambiente
│   ├── models.py                    # PROVIDER_MAP, BUILDERS, Model Enum
│   ├── logging.py                   # ColorFormatter e get_logger
│   ├── decorators.py                # log_tool decorator
│   └── docker.py                    # Auto start/stop do container PostgreSQL
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
| **Guardrail Entrada** | `llama-3.3-70b-versatile` (temp 0.0) | Bloqueia mensagens indevidas e anonimiza PII |
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
| `faq_retriever` | Busca semântica no PDF de FAQ via FAISS + Gemini Embeddings (lazy init) |

---

## Persistência

| Camada | Tecnologia | Responsabilidade |
|---|---|---|
| **Transações e eventos** | PostgreSQL (Docker) | Dados financeiros e de agenda do usuário |
| **Histórico de conversa** | MongoDB | Mensagens por sessão (últimas 5 por consulta) |
| **Checkpointing de grafo** | LangGraph MemorySaver | Estado interno do grafo entre turnos |

O MongoDB armazena duas coleções: `users` (cadastro e perfil comportamental) e `chats` (histórico de mensagens por sessão). O histórico é limitado via projeção `$slice: -5` para evitar contextos longos demais.

O campo `perfil_usuario` — gerado a partir do histórico acumulado e armazenado em `users` — é carregado no estado do grafo antes de cada invocação, servindo como contexto cross-session do usuário.

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
```

Ver [.env.example](.env.example) para a referência completa (inclui `QDRANT_API_KEY` opcional, usada só em instâncias cloud do Qdrant).

### Instalação

```bash
uv venv
uv sync
```

### Execução

```bash
python main.py terminal
```

`tui` ainda não tem implementação (`interfaces/tui/app.py` — ver TODO.md). `api` já tem o app
FastAPI funcional em `interfaces/api/main.py`, mas o dispatcher do `main.py` ainda não o invoca —
hoje a API roda direto via uvicorn (ver TODO.md).

O sistema sobe automaticamente o container Docker do PostgreSQL ao iniciar e o encerra ao fechar.

Digite `/exit` para encerrar.

### Migrations (Alembic)

Schema do PostgreSQL versionado em `alembic/versions/`. Com o container do Postgres no ar
(`POSTGRES_URL` configurado):

```bash
uv run alembic upgrade head
```

O acesso a dados usa SQLAlchemy ORM (`tools/postgres/models.py`), então `--autogenerate` funciona
normalmente a partir daqui:

```bash
uv run alembic revision --autogenerate -m "..."
```

Sempre revise o diff gerado antes de aplicar — e rode `--autogenerate` sem alterações pendentes de
vez em quando pra garantir que os models continuam batendo exatamente com o schema real (diff vazio).

---

## Dependências principais

- [LangChain](https://github.com/langchain-ai/langchain) — framework de agentes e tools
- [LangGraph](https://github.com/langchain-ai/langgraph) — orquestração stateful e checkpointing
- [SQLAlchemy](https://www.sqlalchemy.org/) — ORM sobre o PostgreSQL (`tools/postgres/models.py`), com `psycopg2` como driver
- [Alembic](https://alembic.sqlalchemy.org/) — migrations versionadas do schema PostgreSQL
- [pymongo](https://pymongo.readthedocs.io/) — driver MongoDB para histórico de conversa
- [FAISS](https://github.com/facebookresearch/faiss) — busca vetorial para RAG do FAQ
- [Rich](https://github.com/Textualize/rich) + [pyfiglet](https://github.com/pwaller/pyfiglet) — interface de terminal
- [Pydantic](https://docs.pydantic.dev/) — validação de schemas das tools
- `langchain-anthropic`, `langchain-google-genai`, `langchain-groq` — integrações com providers

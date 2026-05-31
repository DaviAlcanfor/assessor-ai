<div align="center">

<img src="https://img.icons8.com/fluency/96/financial-analytics.png" alt="Assessor.AI" width="96"/>

# Assessor.AI

Assistente pessoal de **finanças e agenda** construído com LangChain + LangGraph.  
O sistema usa uma arquitetura multi-agente onde cada agente tem uma responsabilidade bem definida:  
classificar a intenção, processar o domínio correto e formatar a resposta final para o usuário.

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)
![LangChain](https://img.shields.io/badge/LangChain-1.2-1C3C3C?style=flat&logo=langchain&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-1.1-FF6B35?style=flat)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-psycopg2-336791?style=flat&logo=postgresql&logoColor=white)

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
- Cria, consulta, atualiza e cancela eventos
- Identifica conflitos de horário e sugere alternativas
- Gerencia disponibilidade e lembretes

Para tudo fora desses dois escopos (small talk, saudações, perguntas fora de área), o próprio roteador responde diretamente ao usuário.

---

## Estrutura do projeto
assessor-ai/
├── main.py                      # Ponto de entrada — loop de conversa no terminal
├── requirements.txt             # Dependências do projeto
│
├── agents/
│   ├── prompts/                 # Prompts de cada agente
│   │   ├── base.py              # GenericAgent: persona e contexto temporal compartilhados
│   │   ├── router.py            # RouterAgent
│   │   ├── financeiro.py        # FinanceiroAgent
│   │   ├── agenda.py            # AgendaAgent
│   │   ├── orquestrador.py      # OrquestradorAgent
│   │   └── faq.py               # FaqAgent
│   └── nodes/                   # Funções de nó do grafo LangGraph
│       ├── names.py             # NodeName StrEnum
│       ├── router.py            # no_roteador
│       ├── financeiro.py        # no_financeiro
│       ├── agenda.py            # no_agenda
│       └── orquestrador.py      # no_orquestrador
│
├── graph/
│   ├── state.py                 # Estado e Route StrEnum
│   ├── llms.py                  # build_llm e instâncias de LLM
│   ├── agents.py                # Agentes compilados (router_app, financeiro_app, etc.)
│   └── builder.py               # Construção e compilação do grafo LangGraph
│
├── tools/
│   ├── postgres/
│   │   ├── connection.py        # Pool de conexões PostgreSQL
│   │   ├── helpers.py           # resolve_type_id, get_category_id, local_date_filter_sql
│   │   ├── schemas.py           # Schemas Pydantic das tools
│   │   └── core.py              # Tools LangChain (add, query, update, balance)
│   ├── faq_tools.py             # Tool de RAG sobre o PDF de FAQ
│   └── response.py              # Classe Response para padronizar retornos
│
├── config/
│   ├── settings.py              # Carrega e valida variáveis de ambiente
│   ├── models.py                # PROVIDER_MAP, BUILDERS, Model Enum
│   ├── logging.py               # ColorFormatter e get_logger
│   └── decorators.py            # log_tool decorator
│
├── ui/
│   └── terminal.py              # Interface Rich + pyfiglet no terminal
│
└── data/
└── documents/               # PDFs para RAG
└── FAQ_assessor_v1.1.pdf

---

## Fluxo dos agentes

O fluxo completo de uma mensagem segue quatro etapas:
Usuário
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
│  formata a resposta em linguagem natural
▼
Usuário

### Agentes em detalhe

| Agente | Modelo | Responsabilidade |
|---|---|---|
| **Router** | `llama-3.3-70b-versatile` (temp 0.0) | Classifica a intenção e emite `ROUTE=financeiro\|agenda\|faq`, ou responde diretamente |
| **Financeiro** | `gemini-2.5-flash` + fallback `llama-3.3-70b` | Interpreta a pergunta financeira e chama as tools do banco |
| **Agenda** | `llama-3.3-70b-versatile` (temp 0.0) | Interpreta perguntas de agenda |
| **FAQ** | `llama-3.3-70b-versatile` (temp 0.0) | Consulta o PDF via RAG e responde dúvidas sobre o sistema |
| **Orquestrador** | `llama-3.3-70b-versatile` (temp 0.0) | Formata a resposta do especialista em linguagem natural |

---

## Tools (PostgreSQL)

| Tool | Descrição |
|---|---|
| `add_transaction` | Insere uma transação (amount, tipo, categoria, método de pagamento) |
| `query_transactions` | Consulta transações com filtros por data, tipo e texto |
| `update_transaction` | Atualiza transação por ID ou por busca de texto + data |
| `total_balance` | Retorna saldo total (INCOME − EXPENSES) |
| `daily_balance` | Retorna saldo de um dia específico |

Tipos de transação: `INCOME` (1), `EXPENSES` (2), `TRANSFER` (3).  
Categorias: `comida`, `besteira`, `estudo`, `férias`, `transporte`, `moradia`, `saúde`, `lazer`, `contas`, `investimento`, `presente`, `outros`.

---

## Configuração

### Variáveis de ambiente

```env
GEMINI_API_KEY=...
GROQ_API_KEY=...
DATABASE_URI=postgresql://usuario:senha@host:5432/banco
```

### Instalação

```bash
uv venv
uv pip install -r requirements.txt
```

### Execução

```bash
python main.py
```

Digite `/exit` para encerrar.

---

## Dependências principais

- [LangChain](https://github.com/langchain-ai/langchain) — framework de agentes e tools
- [LangGraph](https://github.com/langchain-ai/langgraph) — orquestração stateful e checkpointing
- [psycopg2](https://pypi.org/project/psycopg2/) — driver PostgreSQL com connection pool
- [Rich](https://github.com/Textualize/rich) + [pyfiglet](https://github.com/pwaller/pyfiglet) — interface de terminal
- [Pydantic](https://docs.pydantic.dev/) — validação de schemas das tools
- `langchain-anthropic`, `langchain-google-genai`, `langchain-groq` — integrações com providers
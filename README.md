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

```
assessor-ai/
├── main.py               # Ponto de entrada — instancia LLMs, agentes e executa o loop de conversa
├── config.py             # Carrega variáveis de ambiente (.env)
├── requirements.txt      # Dependências do projeto
│
├── agents/
│   ├── base.py           # GenericAgent: persona e contexto temporal compartilhados
│   ├── router.py         # RouterAgent: classifica a intenção e emite o protocolo de rota
│   ├── financeiro.py     # FinanceiroAgent: processa perguntas financeiras via tools
│   ├── agenda.py         # AgendaAgent: processa perguntas de agenda/compromissos
│   └── orquestrador.py   # OrquestradorAgent: formata o JSON do especialista em resposta final
│
├── tools/
│   ├── pg_tools.py       # Tools LangChain para PostgreSQL (transações financeiras)
│   ├── schemas.py        # Schemas Pydantic dos argumentos das tools
│   └── response.py       # Helper para padronizar respostas das tools
│
└── docs/
    └── fluxo_agentes.png # Diagrama do fluxo entre agentes
```

---

## Fluxo dos agentes

![Fluxo dos agentes](docs/fluxo_agentes.png)

O fluxo completo de uma mensagem segue quatro etapas:

```
Usuário
  │
  ▼
[Router]  ──── small talk / fora de escopo ───► responde diretamente ao usuário
  │
  │ ROUTE=financeiro|agenda
  ▼
[Especialista]  (Financeiro ou Agenda)
  │  consulta/escreve no banco via tools
  │  retorna JSON estruturado
  ▼
[Orquestrador]
  │  formata o JSON em linguagem natural
  ▼
Usuário
```

### Agentes em detalhe

| Agente | Modelo | Responsabilidade |
|---|---|---|
| **Router** | `llama-3.3-70b-versatile` (temp 0.0) | Classifica a intenção e emite `ROUTE=financeiro\|agenda`, ou responde diretamente em casos de saudação/fora de escopo |
| **Financeiro** | `gemini-2.5-flash` + fallback `llama-3.3-70b` | Interpreta a pergunta financeira, chama as tools do banco e retorna JSON estruturado |
| **Agenda** | `llama-3.3-70b-versatile` (temp 0.0) | Interpreta a pergunta de agenda e retorna JSON estruturado com evento, janela de tempo e intenção |
| **Orquestrador** | `llama-3.3-70b-versatile` (temp 0.0) | Recebe o JSON do especialista e entrega a resposta final formatada ao usuário em português |

O Router usa `MemorySaver` do LangGraph para manter histórico de conversa por sessão. Os especialistas são stateless — recebem o protocolo de rota como entrada e respondem com JSON puro.

---

## Modelos e providers suportados

| Provider | Modelos |
|---|---|
| Google (Gemini) | `gemini-2.5-flash` |
| Groq | `llama-3.3-70b-versatile`, `qwen-2.5-pro` |
| Anthropic (Claude) | `claude-haiku-4-5`, `claude-sonnet-4-6` |

A função `build_llm` em [main.py](main.py) seleciona automaticamente o provider e a API key com base no modelo informado.

---

## Tools (PostgreSQL)

As tools são funções LangChain decoradas com `@tool` que permitem ao agente Financeiro ler e escrever no banco:

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

Crie um arquivo `.env` na raiz do projeto:

```env
GEMINI_API_KEY=...
GROQ_API_KEY=...
ANTHROPIC_API_KEY=...
DATABASE_URI=postgresql://usuario:senha@host:5432/banco
```

### Instalação

```bash
pip install -r requirements.txt
```

### Execução

```bash
python main.py
```

O sistema inicia um loop de conversa no terminal. Use `Ctrl+C` para encerrar.

---

## Dependências principais

- [LangChain](https://github.com/langchain-ai/langchain) — framework de agentes e tools
- [LangGraph](https://github.com/langchain-ai/langgraph) — orquestração stateful e checkpointing
- [psycopg2](https://pypi.org/project/psycopg2/) — driver PostgreSQL
- [Pydantic](https://docs.pydantic.dev/) — validação de schemas das tools
- `langchain-anthropic`, `langchain-google-genai`, `langchain-groq` — integrações com os providers

# AGENTS.md

Contexto do projeto **Assessor.AI** para agentes de IA (Claude Code, Copilot, etc.) trabalhando neste repositório.

## O que é

Assistente pessoal de **finanças** e **agenda** construído com LangChain + LangGraph. Arquitetura
multi-agente: um grafo de nós onde cada nó tem responsabilidade única (guardrail, roteamento,
especialista de domínio, orquestração de resposta). Interface atual é um loop de terminal (Rich +
pyfiglet). Detalhes completos de arquitetura, fluxo de agentes e tools estão no [README.md](README.md)
— leia-o antes de mexer em `agents/` ou `graph/`.

## Stack

- Python 3.13+, gerenciado com `uv` (`uv venv`, `uv sync`, `uv add <pkg>`)
- LangChain 1.2 / LangGraph 1.1 para orquestração de agentes
- LLMs: Gemini (`gemini-2.5-flash`), Groq (`llama-3.3-70b-versatile`), com Claude e Qwen mapeados em
  `config/models.py` mas ainda não usados por nenhum agente
- PostgreSQL (via Docker, auto start/stop em `config/docker.py`) para transações e eventos
- MongoDB para histórico de conversa e perfil de usuário
- FAISS + Gemini Embeddings para RAG do FAQ
- Redis está em `pyproject.toml` como dependência mas **ainda não tem nenhuma tool implementada**
  (ver TODO.md)

## Estrutura

```
agents/     prompts (agents/prompts) e nós de grafo (agents/nodes) — um arquivo por agente
graph/      state.py (estado + Route), llm.py (builders), agents.py (apps compilados), builder.py (grafo)
tools/      integrações externas: tools/postgres/{financeiro,agenda}, tools/mongo/{chats,users}, faq_tools.py
config/     settings.py (env vars via pydantic-settings), models.py (Model enum + providers), docker.py, logging.py
ui/         terminal.py — interface Rich atual (candidata a virar TUI com Textual, ver TODO.md)
data/       documents/ — PDFs para RAG
```

Padrão de cada domínio de tool: `schemas.py` (Pydantic) + `core.py` (as tools em si) + `connection.py`
(conexão lazy, só inicializa no primeiro uso). Siga esse padrão para qualquer tool nova (redis, qdrant, etc).

## Convenções

- Código de domínio (nomes de função, variáveis, docstrings de tool, mensagens ao usuário) é em
  **português**; nomes de classes/tipos de infraestrutura (`Settings`, `Model`, `Route`) em inglês.
  Siga o idioma já usado no arquivo que você está editando.
- Enums de domínio usam `StrEnum` (ver `graph/state.py:Route`, `agents/nodes/names.py:NodeName`).
- Conexões com banco (Postgres, Mongo) são **lazy** — inicializadas só na primeira operação, nunca
  no import do módulo. Mantenha esse padrão para novas integrações (Redis, Qdrant).
- Tools retornam a classe `Response` (`tools/response.py`) para padronizar sucesso/erro.
- Não commitar `.env`; usar `.env.example` como referência de variáveis novas.

## Comandos

```bash
uv venv && uv sync     # instalar dependências
python main.py         # rodar o assistente (sobe o container Postgres automaticamente)
```

Não há suíte de testes no projeto ainda.

## Ao adicionar uma tool nova

1. Criar `tools/<sistema>/schemas.py` com os modelos Pydantic de entrada/saída.
2. Criar `tools/<sistema>/core.py` com as funções decoradas como tool (ver `config/decorators.py:log_tool`).
3. Se for um serviço externo com estado de conexão, criar `connection.py` com init lazy.
4. Registrar a tool no agente correspondente em `agents/nodes/`.
5. Atualizar a tabela de tools no README.md.

## Claude Code

Para instruções específicas de como o Claude Code deve operar neste repo, ver [CLAUDE.md](CLAUDE.md).

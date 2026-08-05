# AGENTS.md

Contexto do projeto **Assessor.AI** para agentes de IA (Claude Code, Copilot, etc.) trabalhando neste repositório.

## O que é

Assistente pessoal de **finanças** e **agenda** construído com LangChain + LangGraph. Arquitetura
multi-agente: um grafo de nós onde cada nó tem responsabilidade única (guardrail, roteamento,
especialista de domínio, orquestração de resposta). `main.py` é um dispatcher (`python main.py
terminal|tui|api`); hoje só `terminal` tem implementação — `tui` e `api` são stubs vazios (ver
TODO.md). Detalhes completos de arquitetura, fluxo de agentes e tools estão no
[README.md](README.md) — leia-o antes de mexer em `agents/` ou `graph/`.

## Stack

- Python 3.13+, gerenciado com `uv` (`uv venv`, `uv sync`, `uv add <pkg>`)
- LangChain 1.2 / LangGraph 1.1 para orquestração de agentes
- LLMs: Gemini (`gemini-2.5-flash`), Groq (`llama-3.3-70b-versatile`), com Claude e Qwen mapeados em
  `config/models.py` mas ainda não usados por nenhum agente
- PostgreSQL (via Docker, auto start/stop em `config/docker.py`) para transações e eventos, acessado
  via SQLAlchemy ORM (`tools/postgres/models.py`) + Alembic pra migrations
- MongoDB para histórico de conversa e perfil de usuário
- FAISS + Gemini Embeddings para RAG do FAQ
- Redis está em `pyproject.toml` como dependência mas **ainda não tem nenhuma tool implementada**
  (ver TODO.md)

## Estrutura

```
chat/       service.py (API pública), runner.py (invoca o grafo), repositories.py (Mongo/Postgres), models.py
interfaces/ um pacote por forma de uso: terminal/{app.py,display.py} (implementado), tui/app.py e api/app.py (vazios)
agents/     prompts (agents/prompts) e nós de grafo (agents/nodes) — um arquivo por agente
graph/      state.py (estado + Route), llm.py (builders), agents.py (apps compilados), builder.py (grafo)
tools/      integrações externas: tools/postgres/{financeiro,agenda}, tools/mongo/{chats,users}, faq_tools.py
config/     settings.py (env vars via pydantic-settings), models.py (Model enum + providers), docker.py, logging.py
data/       documents/ — PDFs para RAG
```

Nenhuma interface (`interfaces/*`) deve chamar `graph/builder.py`, `tools/mongo/*` ou
`tools/postgres/*` diretamente — sempre via `chat/service.py`. É esse limite que permite TUI e API
existirem sem duplicar a lógica de montar estado, invocar o grafo e persistir histórico.

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
- **Tools do LLM nunca recebem `user_id` como argumento.** Args de tool são escolhidos pelo LLM via
  tool-calling — qualquer dado de escopo/permissão (ex. `user_id`) não pode vir por ali. O padrão é
  um `contextvars.ContextVar` setado uma vez por request (`chat/runner.py:executar`, a partir do
  `user_id` já conhecido em `chat/service.py`) e lido dentro da tool
  (`tools/postgres/connection.py:current_user_id()`). Ver uso em `tools/postgres/{financeiro,agenda}/core.py`.
- Não commitar `.env`; usar `.env.example` como referência de variáveis novas.
- **Simplicidade acima de tudo.** Projeto pessoal em estágio inicial — prefira a solução direta à
  abstração "flexível para o futuro". Sem camada genérica, sem config plugável, sem interface para
  uma única implementação. Se dá pra resolver com uma função e um `if`, não vira classe/padrão de
  projeto. Isso vale tanto para código de domínio quanto para infra.

## Fluxo de trabalho (Git)

- Mudança de qualquer tamanho (feature, fix, refactor) vai em **branch própria**, nunca commit
  direto em `main` — exceção só pra coisas triviais tipo ajuste de README/badge, que o próprio
  histórico do repo já mostra indo direto (`git log --oneline`).
- Nome de branch segue `tipo/slug-curto-em-ingles-ou-portugues`, mesmo padrão já usado no repo:
  `feat/perfil-usuario`, `fix/guardrail-falso-positivo`, `refactor/mongo-tools`. Tipos comuns:
  `feat`, `fix`, `refactor`, `chore`.
  - Ao dar deploy/criar branch como agente, use o mesmo prefixo do tipo de mudança.
- Commits seguem o padrão `tipo: descrição curta` (`feat:`, `fix:`, `chore:`) — ver `git log` para
  exemplos reais.
- Mudança termina em **Pull Request** para `main`, mesmo em projeto pessoal — mantém o histórico de
  `git log --all --graph` navegável e dá um ponto de review antes do merge.

## Padrões de organização e clean code

Padrões já em uso no repo — mantenha-os ao adicionar código novo:

- **Package by feature, não por camada técnica.** `tools/postgres/{financeiro,agenda}`,
  `tools/mongo/{chats,users}` — cada domínio é uma pasta com tudo que ele precisa, em vez de um
  `models/`, `services/`, `schemas/` genéricos misturando domínios. Ao criar Redis/Qdrant, seguir o
  mesmo corte: `tools/<sistema>/<domínio>/`.
- **Repository leve por domínio.** `core.py` expõe as operações (`buscar`, `criar`, `atualizar_*`)
  como funções de módulo, não classes — é o repository pattern sem cerimônia de classe/interface.
  `schemas.py` ao lado define o contrato de dados (Pydantic) separado da lógica.
- **Infra isolada e lazy.** Toda conexão externa (`tools/postgres/connection.py`,
  `tools/mongo/connection.py`, `tools/faq_tools.py`) inicializa só no primeiro uso — nunca há
  side effect de I/O no import de um módulo. Isso é o que torna o projeto testável sem mockar tudo
  na importação.
- **ORM sobre Postgres, mas cada tool continua com seu próprio `try/except`.**
  `tools/postgres/models.py` tem os models declarativos; `connection.py:get_session()` já faz
  `commit()`/`rollback()` automático (a tool não chama mais isso na mão). Mas o `try/except Exception
  as e: return Response.error(e)` dentro de cada tool continua obrigatório — `log_tool`
  (`config/decorators.py`) não captura exceção nenhuma, só inspeciona `result["status"]`, então uma
  tool que deixar uma exception escapar quebra o turno inteiro no `except` genérico do chamador em
  vez de devolver um erro estruturado pro LLM reagir.
- **Single responsibility por nó de agente.** `agents/nodes/` (execução) fica separado de
  `agents/prompts/` (conteúdo/persona) — mudar o texto de um prompt nunca deveria exigir tocar na
  lógica de roteamento do grafo, e vice-versa.
- **Contrato de retorno único.** Tools não retornam dict cru nem deixam exception vazar para o
  agente — usam `Response` (`tools/response.py`) como envelope padrão de sucesso/erro. Ao criar
  tool nova, reusar essa classe em vez de inventar outro formato de retorno.
- **Config centralizada.** Uma única fonte de env vars (`config/settings.py`, `pydantic-settings`)
  e um único enum fechado de modelos/providers (`config/models.py:Model`/`PROVIDER_MAP`). Não ler
  `os.environ` direto em outros módulos.
- **Entrypoint fino.** `main.py` só faz dispatch por argv (`terminal`/`tui`/`api`) — nenhuma lógica
  de negócio nele. Lógica de negócio nova vai em `chat/`, nunca de volta pra `main.py`.
- **Camadas de `chat/` + `interfaces/`** seguem uma separação tipo clean architecture bem
  simplificada: `interfaces/*` (I/O — terminal, TUI, HTTP) → `chat/service.py` (casos de uso) →
  `chat/runner.py` + `chat/repositories.py` (LangGraph e persistência). `chat/models.py` define o
  contrato (`ChatMessage`, `Role`) independente dos schemas do Mongo — `chat/repositories.py` é
  quem converte entre os dois.

## Comandos

```bash
uv venv && uv sync       # instalar dependências
python main.py terminal # rodar o assistente no terminal (sobe o container Postgres automaticamente)
```

Não há suíte de testes no projeto ainda.

## Ao adicionar uma tool nova

1. Criar `tools/<sistema>/schemas.py` com os modelos Pydantic de entrada/saída.
2. Criar `tools/<sistema>/core.py` com as funções decoradas como tool (ver `config/decorators.py:log_tool`).
3. Se for um serviço externo com estado de conexão, criar `connection.py` com init lazy.
4. Se a tool precisa ser escopada por usuário, usar `current_user_id()`
   (`tools/postgres/connection.py`) — nunca adicionar `user_id` ao `args_schema` da tool.
5. Registrar a tool no agente correspondente em `agents/nodes/`.
6. Atualizar a tabela de tools no README.md.

## Claude Code

Para instruções específicas de como o Claude Code deve operar neste repo, ver [CLAUDE.md](CLAUDE.md).

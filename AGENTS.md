# AGENTS.md

Contexto do projeto **Assessor.AI** para agentes de IA (Claude Code, Copilot, etc.) trabalhando neste repositório.

## O que é

Assistente pessoal de **finanças** e **agenda** construído com LangChain + LangGraph. Arquitetura
multi-agente: um grafo de nós onde cada nó tem responsabilidade única (guardrail, roteamento,
especialista de domínio, orquestração de resposta). `main.py` é um dispatcher (`python main.py
terminal|tui|api`) — as três interfaces têm implementação real hoje (ver TODO.md pra pendências
específicas de cada uma, ex. streaming na API). Detalhes completos de arquitetura, fluxo de agentes
e tools estão no [README.md](README.md) — leia-o antes de mexer em `agents/` ou `graph/`.

## Stack

- Python 3.13+, gerenciado com `uv` (`uv venv`, `uv sync`, `uv add <pkg>`)
- LangChain 1.2 / LangGraph 1.1 para orquestração de agentes
- LLMs: Gemini (`gemini-2.5-flash`), Groq (`llama-3.3-70b-versatile`), com Claude e Qwen mapeados em
  `core/models.py` mas ainda não usados por nenhum agente
- PostgreSQL para transações e eventos, acessado via SQLAlchemy ORM (`tools/{financeiro,agenda,usuarios}/models.py`) +
  Alembic pra migrations
- MongoDB para histórico de conversa, perfil de usuário e checkpoint do LangGraph (`MongoDBSaver`)
- Qdrant para RAG do FAQ (`tools/faq/`) — substituiu o FAISS local
- Redis para rate limit por usuário, alocação de API key e cache de perfil (`tools/infra/redis.py`)
- Postgres/Mongo/Redis/Qdrant são todos serviços em nuvem — não há infra local via Docker
  (`config/docker.py` e `docker-compose.yml` foram removidos no commit `16479fa`); `.env` aponta
  direto para os serviços hospedados
- FastAPI (`api/`) com auth por API key, rate limiting (`slowapi` por IP + Redis por
  `user_id`) e `fastapi-guard`; o grafo é compilado uma vez no `lifespan`, nunca por request.
  Textual (`tui/`) pra TUI
- `pytest` (`tests/`, espelhando a estrutura de `tools/`) + `ruff` (lint/format) + CI no GitHub
  Actions

## Estrutura

```
src/assessor_ai/   o pacote (layout src/); `main.py` na raiz é só o dispatcher de modo
chat/       service.py (API pública), runner.py (invoca o grafo), repositories.py (Mongo/Postgres), models.py, exceptions.py (erros de domínio)
api/        camada HTTP: app.py, lifespan.py, exception_handlers.py, auth.py, gen_key.py, routes/
services/   casos de uso, sem HTTP: chat_service.py, runner.py, exceptions.py
repositories/ chat_repository.py — fachada sobre tools/chats, tools/usuarios e core/cache
schemas/    contratos de dados: models.py (ChatMessage/Role, interno), chat.py, errors.py, health.py, key.py, user.py
tui/        interface Textual; a2a/ protocolo A2A montado no mesmo app FastAPI
agents/     nós de grafo (agents/nodes) — um arquivo por agente
graph/      state.py (estado + Route), llm.py (builders), agents.py (apps compilados), builder.py (grafo)
tools/      uma pasta por feature (financeiro, agenda, faq, chats, usuarios) com models.py + schemas.py + repo.py;
            tools/infra/ guarda as conexões (postgres, mongo, redis, qdrant) e as bases PostgresRepo/MongoRepo
core/       infra transversal, sem dependência de camada: config.py (env vars), models.py (Model enum + providers),
            logging.py (get_logger + log_tool), privacy.py (PII), prompts/ (.md + loader), cache.py (perfil no Redis),
            limiter.py (slowapi por IP + cota por user_id), middleware.py (fastapi-guard)
tests/      espelha src/assessor_ai/ — só funções puras e serviços com grafo/I/O mockado (ver TODO.md)
data/       documents/ — PDFs para RAG
```

Nenhuma camada de entrega (`api/`, `tui/`, `a2a/`) deve chamar `graph/builder.py` nem os `*Repo`
de `tools/` diretamente — sempre via `services/chat_service.py`, que por sua vez fala com
`repositories/` e `services/runner.py`. É esse limite que permite TUI, API e A2A existirem sem
duplicar a lógica de montar estado, invocar o grafo e persistir histórico.

Padrão de cada feature: `models.py` (ORM, se usa Postgres) + `schemas.py` (Pydantic) + `repo.py` (uma
classe `*Repo`, conexão injetada no construtor). Quem tem tool do LLM expõe `as_tools()`; quem é
interno (chats, usuarios) é só chamado por `repositories/`. Conexão nova vai em `tools/infra/`, nunca
numa pasta de feature.

## Ciclo de vida de uma mensagem

Vale pras três interfaces; o caminho abaixo é o da API, que é o mais longo:

1. **HTTP** — `SecurityMiddleware` (`fastapi-guard`) e `slowapi` (limite por IP) rodam antes da rota.
2. **Auth** — `get_current_user` (`api/auth.py`) troca o header `X-API-Key` por um
   `user_id` guardado no Redis. `user_id` nunca vem do corpo nem da query da request.
3. **Ownership** — `chat_service.validar_ownership` confere que o `chat_id` é do usuário e
   levanta `ChatNaoEncontrado`/`ChatDeOutroUsuario`; a rota não trata, quem traduz pra 404/403 é
   `api/exception_handlers.py`.
4. **Caso de uso** — `services/chat_service.py:send_message`: rate limit por `user_id` no Redis
   (`LimiteDeMensagensExcedido` → 429), carrega histórico/perfil e persiste a mensagem.
5. **Escopo** — `services/runner.py:executar` seta o `ContextVar` de `user_id` e chama
   `fluxo_agentes().invoke(...)`. Toda tool lê o usuário daí, nunca dos args escolhidos pelo LLM.
6. **Grafo** — guardrail de entrada → router → especialista (tools) → orquestrador → guardrail de
   saída (fluxo detalhado no README).
7. **Persistência** — a resposta volta pro `service`, que grava no Mongo (histórico + checkpoint do
   LangGraph); `encerrar_sessao` gera resumo/perfil e invalida o cache de perfil no Redis.
8. **Resposta** — a rota devolve o schema de `schemas/`. Erro é sempre
   `ErrorResponse{detail, code}`: os erros de domínio de `services/exceptions.py` viram 404/403/429/502
   pelos handlers de `api/exception_handlers.py`, e o handler de `Exception` fecha a lista com um 500
   genérico — loga o traceback real, nunca devolve `str(exc)` pro cliente.

Quebrar esse encadeamento (interface chamando grafo/tool direto, tool recebendo `user_id` por
argumento) é o tipo de mudança que passa nos testes e vaza dado entre usuários.

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
  um `contextvars.ContextVar` setado uma vez por request (`services/runner.py:executar`, a partir do
  `user_id` já conhecido em `services/chat_service.py`) e lido dentro da tool
  (`tools/infra/postgres.py:current_user_id()`, exposto como `self.usuario` no `PostgresRepo`). Ver uso em `tools/{financeiro,agenda}/repo.py`.
- Não commitar `.env`; usar `.env.example` como referência de variáveis novas.
- **Simplicidade com coesão.** A régua é "a coisa mais simples que ainda é navegável e coesa", não
  "menor número de linhas". Classe é bem-vinda quando agrupa estado + comportamento que andam juntos
  (ex. ciclo de vida de conexão: init lazy + health + dispose). Continua barrado: interface/factory
  com uma única implementação, camada plugável, config pra valor que nunca muda, e "manager" que só
  guarda referência sem comportamento próprio. Sinal de que falta um objeto/módulo (não mais uma
  função): a função fica órfã sem lugar óbvio, ou o arquivo já passou de ~15 funções soltas de
  contextos diferentes. Vale para código de domínio e infra.

## Regras de operação para agentes

- **Não escrever nem editar código sem permissão explícita.** Investigar, ler, buscar, propor
  diff/plano é livre — mas só encoste em arquivo de código depois de um "pode fazer" literal do
  usuário. Vale para qualquer arquivo versionado (código, config, doc); rascunho em scratchpad é livre.
- **Antes de escrever código: ler, verificar, planejar.** Leia os arquivos que a mudança toca e
  trace o fluxo real de ponta a ponta; confirme versão de lib e API na doc atual (`.agents/skills/`);
  monte um plano do que vai mudar e onde. Só então escreva — pensando na qualidade da implementação
  (menor diff que resolve de fato, encaixe nos padrões do repo, sem abstração especulativa), não na
  primeira coisa que compila.
- **Não deletar arquivo ou pasta sem permissão explícita** — inclusive arquivo que o próprio agente
  criou. Se algo parece obsoleto, diga qual é e por quê, e espere a resposta.
- **Comando destrutivo só com autorização literal:** `git reset --hard`, `git clean -fd`, `rm -rf`,
  `git push --force`, `DROP`/`TRUNCATE` em banco. Tente antes o caminho não destrutivo (`git status`,
  `git diff`, `git stash`, cópia de backup, migration nova).
- **Nada de mudança em massa por script/regex.** Refactor amplo se faz arquivo a arquivo — `sed`
  em cima de código gera estrago silencioso que o lint não pega.
- **Nada de arquivo-variação.** Não existe `service_v2.py`, `app_novo.py`, `main_melhorado.py` —
  revise o arquivo existente. Arquivo novo só pra responsabilidade genuinamente nova (a régua é
  alta; ver "package by feature" acima).
- **Sem shim de compatibilidade.** Projeto pessoal, sem consumidor externo: quando um contrato muda,
  atualize todos os chamadores e siga. Nada de wrapper "deprecated" mantendo assinatura antiga viva.
- **Na dúvida sobre uma lib, leia a doc atual** antes de escrever pelo que você lembra — as versões
  aqui são recentes (LangChain 1.2, LangGraph 1.1, Pydantic 2.13, SQLAlchemy 2.0) e mudaram API.
  Comece por `.agents/skills/`, que já é achado deste repo.
- **Trabalho não terminado vira linha no TODO.md**, não comentário solto no código.

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

- **Package by feature nas tools.** `tools/{financeiro,agenda,faq,chats,usuarios}` — uma pasta por
  domínio, não por banco (`usuarios` sozinho fala com os três), em vez de um
  `models/`, `services/`, `schemas/` genéricos misturando domínios. Ao criar Redis/Qdrant, seguir o
  mesmo corte: `tools/<sistema>/<domínio>/`.
- **Repository leve por domínio.** `core.py` expõe as operações (`buscar`, `criar`, `atualizar_*`)
  como funções de módulo, não classes — é o repository pattern sem cerimônia de classe/interface.
  `schemas.py` ao lado define o contrato de dados (Pydantic) separado da lógica. Exceção: quando o
  módulo carrega estado de ciclo de vida (conexão lazy + pool + health + dispose), aí uma classe que
  encapsula esse estado + comportamento (`infra/postgres.py:PostgresConn`) é preferível a globais
  soltas + funções.
- **Infra isolada e lazy.** Toda conexão externa (`tools/infra/{postgres,mongo,redis,qdrant}.py`)
  inicializa só no primeiro uso — nunca há
  side effect de I/O no import de um módulo. Isso é o que torna o projeto testável sem mockar tudo
  na importação.
- **ORM sobre Postgres, mas cada tool continua com seu próprio `try/except`.**
  `tools/{financeiro,agenda,usuarios}/models.py` tem os models declarativos; `connection.py:get_session()` já faz
  `commit()`/`rollback()` automático (a tool não chama mais isso na mão). Mas o `try/except Exception
  as e: return Response.error(e)` dentro de cada tool continua obrigatório — `log_tool`
  (`core/logging.py`) não captura exceção nenhuma, só inspeciona `result["status"]`, então uma
  tool que deixar uma exception escapar quebra o turno inteiro no `except` genérico do chamador em
  vez de devolver um erro estruturado pro LLM reagir.
- **Single responsibility por nó de agente.** `agents/nodes/` (execução) fica separado de
  `core/prompts/` (conteúdo/persona) — mudar o texto de um prompt nunca deveria exigir tocar na
  lógica de roteamento do grafo, e vice-versa. Prompt é `.md`, não Python: cada arquivo tem
  seções `## PAPEL` / `## SHOTS` (ou templates nomeados, como `## CLASSIFICADOR`) e um frontmatter
  opcional (`usa_tools_obrigatorias: true`). `core/prompts/loader.py` é o único `.py` da pasta —
  `load_prompt(nome)` monta persona + papel + shots, `load_sections(nome)` devolve as seções cruas.
- **Tudo async da ponta ao fim.** Nós do grafo, `services/runner.py`, `services/chat_service.py`,
  `repositories/chat_repository.py` e as rotas da API são `async def`. O grafo roda por `ainvoke` (por isso o
  checkpointer é `AsyncPostgresSaver`, não o síncrono). Os drivers de Mongo/Redis/SQLAlchemy
  continuam síncronos e são chamados via `asyncio.to_thread` em `repositories/chat_repository.py` — função nova
  que faça I/O bloqueante entra pelo mesmo caminho, nunca direto no event loop.
- **Contrato de retorno único.** Tools não retornam dict cru nem deixam exception vazar para o
  agente — usam `Response` (`tools/response.py`) como envelope padrão de sucesso/erro. Ao criar
  tool nova, reusar essa classe em vez de inventar outro formato de retorno.
- **Config centralizada.** Uma única fonte de env vars (`core/config.py`, `pydantic-settings`, com
  toda credencial — inclusive URLs de conexão — como `SecretStr`) e um único enum fechado de
  modelos/providers (`core/models.py:Model`/`PROVIDER_MAP`). Não ler
  `os.environ` direto em outros módulos.
- **Entrypoint fino.** `main.py` só faz dispatch por argv (`terminal`/`tui`/`api`) — nenhuma lógica
  de negócio nele. Lógica de negócio nova vai em `chat/`, nunca de volta pra `main.py`.
- **Camadas por responsabilidade** seguem uma separação tipo clean architecture bem
  simplificada: `api/`/`tui/`/`a2a/` (I/O) → `services/chat_service.py` (casos de uso) →
  `services/runner.py` + `repositories/chat_repository.py` (LangGraph e persistência). `schemas/models.py` define o
  contrato (`ChatMessage`, `Role`) independente dos schemas do Mongo — `repositories/chat_repository.py` é
  quem converte entre os dois.

## Comandos

```bash
uv venv && uv sync        # instalar dependências
python main.py tui        # rodar o assistente (tui | api)
fastapi dev               # subir só a API (entrypoint já está no pyproject.toml)
just check                # ruff check — mesmo lint que roda no CI em push/PR pra main
just fix                  # ruff check --fix
just test                 # pytest
```

### Verificação obrigatória depois de mexer em código

`just check` e `just test`, os dois verdes, **antes** de dar a mudança por terminada. Se um teste já
estava vermelho antes da sua mudança, diga isso explicitamente em vez de deixar passar.

Teste novo cobre caminho feliz, borda (lista vazia, valor no limite, data virando o dia) e erro
(exceção da tool, LLM devolvendo formato inesperado). `tests/` espelha a estrutura do pacote testado.

## Ao adicionar uma tool nova

1. Criar `tools/<feature>/schemas.py` com os modelos Pydantic de entrada/saída (e `models.py`, se
   usar Postgres — nesse caso importar o model no `alembic/env.py`).
2. Criar `tools/<feature>/repo.py` com uma classe `*Repo`. Se for Postgres, herdar de `PostgresRepo`
   e decorar os métodos com `@transacional` (sessão, commit/rollback e `Response.error` de graça).
3. Expor as tools em `as_tools()` com `StructuredTool.from_function(self.metodo, name=...)` —
   **nunca** `@tool` no método, que vaza `self` pro schema mandado ao LLM.
4. Se for um banco/serviço novo, criar a conexão em `tools/infra/` com init lazy — nunca dentro da
   pasta da feature.
5. Se a tool precisa ser escopada por usuário, usar `self.usuario` — nunca adicionar `user_id` ao
   `args_schema` da tool.
6. Instanciar o repo em `tools/__init__.py` e registrar a lista no agente em `graph/agents.py`.
7. Atualizar a tabela de tools no README.md.

## Encerrando a sessão

1. `just check` e `just test` verdes — ou o motivo explícito de não estarem.
2. TODO.md atualizado: item concluído vira `[x]` com o que ficou decidido, achado novo vira `[ ]`.
3. Pegadinha nova de lib vira entrada em `.agents/skills/<lib>.md`.
4. README atualizado se estrutura, tool ou variável de ambiente mudou.
5. Commit `tipo: descrição` em branch própria + PR pra `main`.

## Skills por biblioteca

`.agents/skills/` guarda convenções e pegadinhas específicas de cada lib usada no projeto
(pydantic, fastapi, mongo, langchain, sqlalchemy, redis — um arquivo por lib, regra + exemplo do que
fazer e do que não fazer). `dependencies.md`, `responses.md`, `streaming.md`, `path-operations.md` e
`other-tools.md` são material de referência do skill oficial do FastAPI, linkados a partir do
`fastapi.md`. São achados reais do repo (muitos vêm de bugs já corrigidos, ver TODO.md),
não tutorial genérico. Consulte antes de escrever código novo que toque uma dessas libs; adicione
uma entrada nova quando encontrar uma pegadinha não óbvia que provavelmente vai se repetir.

## Claude Code

Para instruções específicas de como o Claude Code deve operar neste repo, ver [CLAUDE.md](CLAUDE.md).

# AGENTS.md

Contexto do projeto **Assessor.AI** para agentes de IA (Claude Code, Copilot, etc.) trabalhando neste repositório.

## O que é

Assistente pessoal de **finanças** e **agenda** construído com LangChain + LangGraph. Arquitetura
multi-agente: um grafo de nós onde cada nó tem responsabilidade única (guardrail, roteamento,
especialista de domínio, orquestração de resposta). `main.py` é um dispatcher (`python main.py
terminal|tui|api`) — as três interfaces têm implementação real hoje (ver TODO.md pra pendências
específicas de cada uma, ex. streaming na API). Detalhes completos de arquitetura, fluxo de agentes
e tools estão no [README.md](README.md) — leia-o antes de mexer em `graph/` ou `graph/tools/`.

## Stack

- Python 3.13+, gerenciado com `uv` (`uv venv`, `uv sync`, `uv add <pkg>`)
- LangChain 1.2 / LangGraph 1.1 para orquestração de agentes
- LLMs: Gemini (`gemini-2.5-flash`) e Groq (`openai/gpt-oss-120b`), com GPT-6 Luna (Vercel AI Gateway,
  opcional) no fim das cadeias de fallback. Claude e Qwen mapeados em `infra/llm/registry.py` mas fora das cadeias.
  Config por provider em `settings/llm.py` (`settings.llm.<provider>`, `LLM__<PROVIDER>__*` no .env)
- JeV (TypeSafe), pela Decisions API do Vercel AI Gateway (`infra/llm/jev/`): decide sem gerar texto o
  guardrail de entrada e o roteador; se falhar, o LLM assume. Ver `.agents/skills/jev.md`
- PostgreSQL para transações, eventos e checkpoint do LangGraph, acessado via SQLAlchemy ORM (`infra/postgres/models/`) +
  Alembic pra migrations
- MongoDB para histórico de conversa e perfil de usuário
- Qdrant para RAG do FAQ (`graph/tools/faq/`) — substituiu o FAISS local
- Redis para rate limit por usuário, alocação de API key e cache de perfil (`infra/redis/`)
- Postgres/Mongo/Redis/Qdrant são todos serviços em nuvem — não há infra local via Docker; `.env`
  aponta direto para os serviços hospedados
- FastAPI (`api/`) com auth por API key, rate limiting (`slowapi` por IP + Redis por
  `user_id`) e `fastapi-guard`; o grafo é compilado uma vez no `lifespan`, nunca por request.
  Textual (`tui/`) pra TUI
- `pytest` (`tests/`, espelhando a estrutura de `app/`) + `ruff` (lint/format) + CI no GitHub
  Actions

## Estrutura

```
app/                 o pacote (`from app.x import y`); `main.py` na raiz é só o dispatcher de modo
  settings/          pydantic-settings por grupo (api, api_keys, database, llm, mercado, observability)
  domain/            tipos neutros, sem I/O: errors.py (DomainError), types.py, identifiers.py, privacy.py, models/
  schemas/           contratos HTTP (chat, perfil, auth, health...)
  infra/             conexões e clientes externos, um pacote por sistema: postgres/ (+ models/), mongo/, redis/,
                     qdrant/, llm/ (+ jev/), mercado/, logging/, context.py (escopo do usuário do turno)
  repositories/      persistência crua, síncrona: um módulo por agregado (financeiro_, agenda_, usuario_,
                     chat_, perfil_, faq_, categoria_repository)
  services/          casos de uso e regra, async: os ÚNICOS que importam repositories (financeiro_, agenda_,
                     mercado_, user_, auth_, perfil_, faq_, categoria_, health_, memoria_, chat_service + runner)
  graph/             o grafo: nodes/, guardrail/, prompts/ (só .md), tools/, agents.py, state.py, names.py,
                     llm.py, builder.py
  telemetry/         métricas Prometheus (`medir_node`, `medir_externo`) e o callback do LangChain
  api/               portas de entrada HTTP: app.py, lifespan.py, auth/, middleware/, errors/, routes/,
                     a2a/ (protocolo A2A) e mcp/ (servidor MCP)
  tui/               interface Textual
tests/               espelha app/ + test_arquitetura.py (as regras de camada, via `ast`)
data/                documents/ — PDFs para RAG
```

As camadas só importam pra baixo: `domain → settings → infra → repositories → services → graph / api`
(`telemetry` é transversal). `tests/test_arquitetura.py` verifica isso nos imports — se uma mudança
quebrar uma regra, o teste aponta o arquivo e a linha.

**Repository + service andam juntos:** só `services/` importa `repositories/`. Tools, nodes, rotas, MCP, A2A
e TUI chegam aos dados sempre por um service (o `lifespan.py` é a única exceção da API, e está
documentada no teste). Nenhuma porta de entrega chama `graph/builder.py` nem uma tool direto — é
`services/chat_service.py` que fala com `services/runner.py`. É esse limite que permite TUI, API, A2A e
MCP existirem sem duplicar a lógica de montar estado, invocar o grafo e persistir histórico.

Padrão de cada domínio: `infra/postgres/models/<dominio>.py` (ORM, se usa Postgres) →
`repositories/<dominio>_repository.py` (SQL/queries, `user_id` explícito, sem regra) →
`services/<dominio>_service.py` (regra, escopo do usuário via `current_user_id()`, `to_thread`) →
`graph/tools/<dominio>/{schemas,tools}.py` (a `ToolSet` que o LLM vê). Conexão nova vai em `infra/`, nunca
numa pasta de domínio.

## Ciclo de vida de uma mensagem

Vale pras três interfaces; o caminho abaixo é o da API, que é o mais longo:

1. **HTTP** — `SecurityMiddleware` (`fastapi-guard`) e `slowapi` (limite por IP) rodam antes da rota.
2. **Auth** — `get_current_user` (`api/auth/dependencies.py`) troca o header `X-API-Key` por um
   `user_id` guardado no Redis. `user_id` nunca vem do corpo nem da query da request.
3. **Ownership** — `chat_service.validar_ownership` confere que o `chat_id` é do usuário e
   levanta `ChatNaoEncontrado`/`ChatDeOutroUsuario`; a rota não trata, quem traduz pra 404/403 é
   `api/errors/handlers.py`.
4. **Caso de uso** — `services/chat_service.py:send_message`: rate limit por `user_id` no Redis
   (`LimiteDeMensagensExcedido` → 429), carrega histórico/perfil e persiste a mensagem.
5. **Escopo** — `services/runner.py:executar` seta o `ContextVar` de `user_id` e chama
   `fluxo_agentes().ainvoke(...)`. Toda tool lê o usuário daí, nunca dos args escolhidos pelo LLM.
6. **Grafo** — guardrail de entrada → router → especialista (tools) → orquestrador → guardrail de
   saída (fluxo detalhado no README).
7. **Persistência** — a resposta volta pro `service`, que grava o histórico no Mongo e o checkpoint
   do LangGraph no PostgreSQL; `encerrar_sessao` gera resumo/perfil e invalida o cache de perfil no Redis.
8. **Resposta** — a rota devolve o schema de `schemas/`. Erro é sempre
   `ErrorResponse{detail, code}`: os erros de domínio de `domain/errors.py` viram 404/403/429/502 pelos
   handlers de `api/errors/handlers.py` (cada um carrega o `status_code`, o `code` e a `public_message`), e o handler de `Exception` fecha a lista com um 500
   genérico — loga o traceback real, nunca devolve `str(exc)` pro cliente.

Quebrar esse encadeamento (interface chamando grafo/tool direto, tool recebendo `user_id` por
argumento) é o tipo de mudança que passa nos testes e vaza dado entre usuários.

## Convenções

- Código de domínio (nomes de função, variáveis, docstrings de tool, mensagens ao usuário) é em
  **português**; nomes de classes/tipos de infraestrutura (`Settings`, `Model`, `Route`) em inglês.
  Siga o idioma já usado no arquivo que você está editando.
- Enums de domínio usam `StrEnum` quando precisam de validação em runtime (ver `graph/state.py:Route`).
  Para conjuntos fechados usados apenas na tipagem estática, prefira `Literal` e constantes (ver
  `graph/names.py:NodeName`).
- Conexões com banco (Postgres, Mongo) são **lazy** — inicializadas só na primeira operação, nunca
  no import do módulo. Mantenha esse padrão para novas integrações (Redis, Qdrant).
- Tools retornam a classe `Response` (`graph/tools/response.py`) para padronizar sucesso/erro.
- **Tools do LLM nunca recebem `user_id` como argumento.** Args de tool são escolhidos pelo LLM via
  tool-calling — qualquer dado de escopo/permissão (ex. `user_id`) não pode vir por ali. O padrão é
  um `ContextVar` único (`infra/context.py`), aberto com `session_context(user_id)` por quem sabe quem
  é o usuário (o `runner` no chat; o middleware `IdentidadeMCP` no `/mcp`) e lido pelo **service**
  (`current_user_id()`), que passa o `user_id` explícito ao repository. Fora de um `session_context()`
  ele levanta `UsuarioDaSessaoNaoDefinido`: não existe usuário "padrão" que leia dado real.
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

- **Package by domínio.** `graph/tools/{financeiro,agenda,mercado,perfil,faq}` — uma pasta por domínio
  (`schemas.py` + `tools.py`), não por banco. O SQL/Mongo/Qdrant do domínio vive em
  `repositories/<dominio>_repository.py` e a regra em `services/<dominio>_service.py`.
- **Repository = persistência crua, sem regra.** Classe com a conexão injetada no construtor (teste troca
  por SQLite/fake), métodos síncronos, `user_id` sempre explícito, TypedDicts de entrada/saída. Postgres:
  `PostgresRepo` + `@transacional` (abre a sessão, commit/rollback, a exceção sobe intacta).
  `repositories/financeiro_repository.py` é o exemplo.
- **Service = regra + escopo.** Classe com o repository injetável (ou funções de módulo nos services
  mais antigos), métodos `async` que chamam o repository com `asyncio.to_thread`. Levanta `DomainError`
  (`DadosInvalidos`, `RegistroNaoEncontrado`...) em vez de devolver dict de erro.
- **Infra isolada e lazy.** Toda conexão externa (`infra/{postgres,mongo,redis,qdrant}/`) inicializa só no
  primeiro uso — nunca há side effect de I/O no import de um módulo. Isso é o que torna o projeto testável
  sem mockar tudo na importação.
- **Tool = `ToolSet` fina.** `graph/tools/base.py:ToolSet`: cada método público é uma tool; o
  `__init_subclass__` aplica `Response.catch` (exceção vira `Response.error`: erro de domínio devolve a
  `public_message`, qualquer outra coisa vira texto genérico e é logada com traceback) e `Logging.log_classe`
  (log de CHAMANDO/OK/ERRO com PII redigida). O `as_tools()` é automático, a partir do mapa `schemas`
  (nome da tool → `args_schema`) e da docstring. O método só chama o service e devolve `Response.ok(...)`.
- **Single responsibility por nó de agente.** `graph/nodes/` (execução) fica separado de
  `graph/prompts/` (conteúdo/persona) — mudar o texto de um prompt nunca deveria exigir tocar na
  lógica de roteamento do grafo, e vice-versa. Prompt é `.md`, não Python: cada arquivo tem
  seções `## PAPEL` / `## SHOTS` (ou templates nomeados, como `## CLASSIFICADOR`) e um frontmatter
  opcional (`usa_tools_obrigatorias: true`). `graph/prompts/loader.py` é o único `.py` da pasta —
  `load_prompt(nome)` monta persona + papel + shots, `load_sections(nome)` devolve as seções cruas.
- **Tudo async da ponta ao fim.** Nós do grafo, `services/`, tools e as rotas da API são `async def`. O
  grafo roda por `ainvoke` (por isso o checkpointer é `AsyncPostgresSaver`, não o síncrono). Os drivers de
  Mongo/Redis/SQLAlchemy continuam síncronos e são chamados via `asyncio.to_thread` **nos services** — função
  nova que faça I/O bloqueante entra pelo mesmo caminho, nunca direto no event loop.
- **Contrato de retorno único.** Tools não retornam dict cru nem deixam exception vazar para o
  agente — usam `Response` (`graph/tools/response.py`) como envelope padrão de sucesso/erro. Ao criar
  tool nova, reusar essa classe em vez de inventar outro formato de retorno.
- **Config centralizada.** Uma única fonte de env vars (`settings/`, `pydantic-settings`, com
  toda credencial — inclusive URLs de conexão — como `SecretStr`) e um único enum fechado de
  modelos/providers (`settings/llm.py:Model` + `infra/llm/registry.py:PROVIDER_MAP`). Não ler
  `os.environ` direto em outros módulos.
- **Entrypoint fino.** `main.py` só faz dispatch por argv (`terminal`/`tui`/`api`) — nenhuma lógica
  de negócio nele. Lógica de negócio nova vai em `services/`, nunca de volta pra `main.py`.
- **Camadas por responsabilidade:** `api/`/`tui/` (I/O) → `services/` (casos de uso) → `repositories/`
  (persistência) → `infra/` (conexões). `domain/` guarda os tipos, erros e regras neutras que todas usam
  (`ChatMessage`, `DomainError`, PII); `graph/` é o que o `runner` executa.

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

1. Se usa Postgres: model em `infra/postgres/models/<dominio>.py` (e importar em `infra/postgres/models/__init__.py`,
   que o `alembic/env.py` e os testes usam para registrar a tabela).
2. `repositories/<dominio>_repository.py`: classe sobre a conexão (`PostgresRepo` + `@transacional`, ou
   `MongoRepo`), `user_id` explícito, TypedDicts de entrada/saída. API externa em vez de banco: cliente em
   `infra/<sistema>/` (ver `infra/mercado/`: `MercadoClient`, cache, `medir_externo`) e pule o repository.
3. `services/<dominio>_service.py`: regra, validação (`DadosInvalidos`), escopo (`current_user_id()`), `to_thread`.
4. `graph/tools/<dominio>/schemas.py` com os `*Args` Pydantic (`Field(description=...)`) e `tools.py` com uma
   classe que herda `ToolSet`: métodos `async` com docstring, `schemas: ClassVar[Schemas] = {...}`, só chamam o
   service e devolvem `Response.ok(...)`. **Nunca** `user_id` no `args_schema`.
5. Instanciar a classe em `graph/tools/__init__.py` (`*_TOOLS = x.as_tools()`) e passar a lista ao agente em
   `graph/agents.py`. Para o MCP, entrar na lista de `api/mcp/server.py` e em `api/mcp/annotations.py`.
6. Testes: repository (SQLite/fake), service (repository falso) e a tool (`Response`); a regra de camada o
   `tests/test_arquitetura.py` já cobre.
7. Atualizar a tabela de tools no README.md.

## Encerrando a sessão

1. `just check` e `just test` verdes — ou o motivo explícito de não estarem.
2. TODO.md atualizado: item concluído vira `[x]` com o que ficou decidido, achado novo vira `[ ]`.
3. Pegadinha nova de lib vira entrada em `.agents/skills/<lib>.md`.
4. README atualizado se estrutura, tool ou variável de ambiente mudou.
5. Commit `tipo: descrição` em branch própria + PR pra `main`.

## Skills por biblioteca

`.agents/skills/` guarda convenções e pegadinhas específicas de cada lib usada no projeto
(pydantic, fastapi, mongo, langchain, sqlalchemy, redis, jev, mercado — um arquivo por lib, regra + exemplo do que
fazer e do que não fazer). `dependencies.md`, `responses.md`, `streaming.md`, `path-operations.md` e
`other-tools.md` são material de referência do skill oficial do FastAPI, linkados a partir do
`fastapi.md`. São achados reais do repo (muitos vêm de bugs já corrigidos, ver TODO.md),
não tutorial genérico. Consulte antes de escrever código novo que toque uma dessas libs; adicione
uma entrada nova quando encontrar uma pegadinha não óbvia que provavelmente vai se repetir.

## Claude Code

Para instruções específicas de como o Claude Code deve operar neste repo, ver [CLAUDE.md](CLAUDE.md).

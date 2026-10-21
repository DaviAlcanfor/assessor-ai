# MCP (`app/api/mcp/`)

Servidor MCP do Assessor.AI, montado em `/mcp`. Mais uma porta de entrada sobre as mesmas tools que os
agentes usam. Código em `app/api/mcp/`: `server.py` (monta o `MCPServer`), `adapter.py` (tools do LangChain
→ tools MCP), `annotations.py`, `auth.py` (middleware), `resources.py`, `lifespan.py`. Testes em
`tests/api/mcp/` (inclui um que fala o protocolo MCP de verdade). SDK `mcp` 2.x.

## Sem escopo de usuário, a tool levanta (de propósito)

O MCP não passa pelo runner do grafo, que é quem abre o `session_context()` no chat. O middleware
`IdentidadeMCP` (`auth.py`) autentica pelo `X-API-Key` (`auth_service.usuario_da_chave`) e abre o escopo
em volta de cada request; sem chave, 401. Antes disso o `/mcp` rodava como o usuário legado e lia dado
real de qualquer um. Em modo dev (`API__KEY_AUTH_ENABLED=false`) o service devolve o usuário padrão.

## `stateless_http=True` é obrigatório

Com sessão MCP guardada entre chamadas, o `session_context` aberto no request da chave A poderia ser
reaproveitado por quem tem a sessão. Stateless: cada request carrega a própria identidade.

## 421 "Invalid Host header" fora do localhost

O SDK liga uma proteção contra DNS rebinding e só aceita `Host: localhost:<porta>`. Qualquer domínio de
deploy (e `localhost` **sem porta**) vira 421. Configure `API__MCP_ALLOWED_HOSTS=["meuapp.exemplo.com"]`
(`settings.api.mcp_allowed_hosts`). Em teste use `base_url="http://localhost:8000"`.

## O lifespan do sub-app não roda sozinho

Um `Mount` do Starlette não dispara o lifespan do app montado, e o `session_manager.run()` do MCP vive
nele. O lifespan da API entra em `lifespan_mcp(app)` (`lifespan.py`). A instância do sub-app
(`mcp_starlette`) tem que ser a **mesma** no `app.mount()` e no lifespan, e o `session_manager` só roda
**uma vez por instância** (por isso o teste de protocolo usa um cliente por módulo, não por teste).
`streamable_http_path="/"` porque a API já monta em `/mcp` (o padrão duplicaria para `/mcp/mcp`).

## O adaptador monta a assinatura a partir do `args_schema`

O `MCPServer` monta o schema da tool pela assinatura da função. `adapter.py` não copia assinatura à mão:
constrói uma `inspect.Signature` com um parâmetro por campo do `args_schema` Pydantic, em
`Annotated[tipo, Field(description=...), *metadata]`. Resultado: `description`, `ge`/`le` e
`exclusiveMinimum` chegam ao cliente MCP iguais aos que o LLM vê, e tool nova aparece no MCP sozinha
(basta entrar em `FINANCEIRO_TOOLS`/`AGENDA_TOOLS`/`MERCADO_TOOLS` em `server.py`). Chama `tool.ainvoke`:
a tool síncrona roda numa thread que herda o contexto, então o escopo do usuário continua valendo.

## Anotações

`annotations.py` mapeia nome da tool → `ToolAnnotations` (leitura, leitura externa, escrita aditiva,
escrita destrutiva). Tool sem entrada na tabela cai em **destrutiva**: o cliente pede confirmação. Ao
criar tool nova, adicione-a lá.

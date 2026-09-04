# CODE_STYLE.md

Convenções de código do **Assessor.AI**. Leia antes de escrever qualquer código novo, não só na
primeira vez — isso é referência de consulta constante, não onboarding único.

Regras de *operação* do agente (o que pode/não pode fazer, git, comandos destrutivos) ficam no
[AGENTS.md](AGENTS.md). Aqui é só sobre como o código deve ficar.

## Organização e arquitetura

**Duas réguas, uma por região do código — não misture.**

*Por camada, no fluxo de chat.* `api/` (HTTP) → `services/` (casos de uso) → `repositories/`
(persistência), com `schemas/` guardando os contratos de dados. É um fluxo só, com um caso de uso
central (`send_message`) e três entregas diferentes por cima (`api/`, `tui/`, `a2a/`) — o corte
que separa "o que o sistema faz" de "como ele é entregue" é o que evita cada interface reimplementar
a mesma coisa. Arquivo novo de chat entra numa dessas quatro pastas pelo papel que exerce.

*Por feature, nas tools.* `graph/tools/{financeiro,agenda,faq,chats,usuarios}` — uma pasta por domínio
(`models.py` + `schemas.py` + `repo.py`), **não** uma por banco. `usuarios` é a prova de que o corte
por banco estava errado: cadastro no Mongo, linha de FK no Postgres e API key no Redis são a mesma
feature, e enquanto moravam em três pacotes quem chamava tinha que lembrar de acertar os dois
primeiros na ordem certa. As conexões, que aí sim são compartilhadas entre features, ficam em
`infra/`. Feature nova = pasta nova em `graph/tools/`; banco novo = arquivo novo em `infra/`.

A régua é a mesma nos dois casos — junto o que muda junto. Muda o que "junto" significa.

**Um `*Repo` por feature, conexão injetada no construtor.** `repo.py` expõe as operações como
métodos (`buscar`, `criar`, `atualizar_*`); a conexão entra por parâmetro com default no singleton
(`FinanceiroRepo(conn=...)`), o que faz o teste trocar Postgres por SQLite sem monkeypatch de
módulo. `schemas.py` ao lado define o contrato de dados (Pydantic), `models.py` os models do ORM.
Nada de classe base abstrata ou interface — as bases (`PostgresRepo`, `MongoRepo`) são concretas e
só carregam conexão + logger.

**Nenhum `with session()` no corpo de uma operação de Postgres.** `@transacional`
(`infra/postgres.py`) abre a sessão, injeta como 2º parâmetro, faz commit/rollback, loga e
converte exceção em `Response.error` — o método fica só com a query. O decorator também reescreve
`__signature__` pra tirar o parâmetro da sessão: sem isso o `functools.wraps` faz o
`inspect.signature` enxergar `s`, que vaza pro JSON schema mandado ao LLM.

**Tool do LLM se liga na instância, nunca com `@tool` no método.** `@tool` roda no corpo da classe,
quando `self` ainda está na assinatura, e o `self` vira parâmetro obrigatório no schema que o
modelo tenta preencher. O bind correto é `StructuredTool.from_function(repo.metodo, name=...)`
dentro de `as_tools()`. Efeito colateral bom: o teste chama `repo.metodo(...)` direto, sem `.func`.

**Infra isolada e lazy.** Toda conexão externa (`infra/{postgres,mongo,redis,qdrant}.py`) é
uma classe que só abre o client no primeiro acesso — nunca há side effect de I/O no import de um
módulo. As instâncias singleton (`postgres`, `mongo`, `redis`, `qdrant`) podem ser criadas no import
justamente porque o construtor não conecta. Isso é o que torna o projeto testável sem mockar tudo na
importação.

**Nenhuma tool pode deixar exceção escapar.** Uma exception que sobe da tool quebra o turno
inteiro no `except` genérico do chamador, em vez de devolver um erro estruturado pro LLM reagir. Nas
tools de Postgres isso é garantia do `@transacional` (converte tudo em `Response.error`); nas
demais (`faq/repo.py`), o `try/except Exception` no corpo continua obrigatório. Os models
declarativos ficam em `graph/tools/<feature>/models.py`, todos sobre o `Base` de `infra/postgres.py` —
model que não for importado pelo `alembic/env.py` some do metadata e vira um DROP no
`--autogenerate`.

**Single responsibility por nó de agente.** `graph/agents/nodes/` (execução) fica separado de
`graph/agents/prompts/` (conteúdo/persona) — mudar o texto de um prompt nunca deveria exigir tocar na
lógica de roteamento do grafo, e vice-versa. Prompt é `.md`, não Python: cada arquivo tem seções
`## PAPEL` / `## SHOTS` (ou templates nomeados, como `## CLASSIFICADOR`) e um frontmatter opcional
(`usa_tools_obrigatorias: true`). `graph/agents/prompts/loader.py` é o único `.py` da pasta — `load_prompt(nome)`
monta persona + papel + shots, `load_sections(nome)` devolve as seções cruas.

**Tudo async da ponta ao fim.** Nós do grafo, `services/runner.py`, `services/chat_service.py`,
`repositories/chat_repository.py` e as rotas da API são `async def`. O grafo roda por `ainvoke` (por isso o
checkpointer é `AsyncPostgresSaver`, não o síncrono). Os drivers de Mongo/Redis/SQLAlchemy continuam
síncronos e são chamados via `asyncio.to_thread` em `repositories/chat_repository.py` — função nova que faça
I/O bloqueante entra pelo mesmo caminho, nunca direto no event loop.

**Contrato de retorno único.** Tools não retornam dict cru nem deixam exception vazar para o
agente — usam `Response` (`graph/tools/response.py`) como envelope padrão de sucesso/erro. Ao criar tool
nova, reusar essa classe em vez de inventar outro formato de retorno.

**Config centralizada.** Uma única fonte de env vars (`config.py`, `pydantic-settings`) e
um único enum fechado de modelos/providers (`models.py:Model`/`PROVIDER_MAP`). Não ler
`os.environ` direto em outros módulos. Campo que carrega credencial é `SecretStr`, **incluindo as
URLs de conexão** (elas trazem usuário e senha embutidos): o `repr` sai mascarado e o valor real só
sai com `.get_secret_value()` explícito no ponto de uso. Nunca logar o objeto `Settings` inteiro.

**Infra transversal fica na raiz do pacote, sem dependência de camada.** O que tem consumidor em
mais de uma camada fica em `config.py`, `logging.py`, `privacy.py`, `identifiers.py` ou `infra/`
(incluindo `cache.py`) — `api/limiter.py` e `api/middleware.py` pertencem à camada HTTP. Regra
prática: se `graph/agents/`, `services/` e `api/` usam a mesma coisa, ela não pertence a nenhum
dos três.

**Erro de domínio não conhece transporte.** `services/chat_service.py` levanta as exceções de
`services/exceptions.py` (`ChatNaoEncontrado`, `ChatDeOutroUsuario`, `LimiteDeMensagensExcedido`,
`FalhaNoAgente`) — nunca `HTTPException`, porque as mesmas chamadas servem API, TUI e A2A. Quem
traduz pra HTTP é `api/exception_handlers.py`, registrado uma vez na app; rota não tem
`try/except`. Exceção nova entra no `_MAPA` de lá; o handler de `Exception` no fim loga o traceback
e devolve mensagem genérica — `str(exc)` de erro imprevisto pode carregar query ou connection
string.

**Entrypoint fino.** `main.py` só faz dispatch por argv (`tui`/`api`) — nenhuma lógica de
negócio nele. Lógica de negócio nova vai em `services/`, nunca de volta pra `main.py`.

**Recurso caro se monta uma vez, no lifespan.** O grafo e o checkpointer (`fluxo_agentes()`) são
compilados no `lifespan` de `api/app.py`, nunca dentro de uma rota: `setup()` do
checkpointer cria tabelas no Postgres, e pagar isso num request faz o primeiro usuário do deploy
esperar por infra. Recriar o checkpointer por request também perderia o histórico turno a turno.

**Camadas por responsabilidade** seguem uma separação tipo clean architecture bem
simplificada: `api/`, `tui/` e `a2a/` (I/O) → `services/chat_service.py` (casos de uso) →
`services/runner.py` + `repositories/chat_repository.py` (LangGraph e persistência). `schemas/models.py` define o
contrato (`ChatMessage`, `Role`) independente dos schemas do Mongo — `repositories/chat_repository.py` é quem
converte entre os dois.

**Simplicidade com coesão.** A régua é "a coisa mais simples que ainda é navegável e coesa", não
"menor número de linhas". Classe é bem-vinda quando agrupa estado + comportamento que andam juntos
(ex. ciclo de vida de conexão: init lazy + health + dispose). Continua barrado: interface/factory
com uma única implementação, camada plugável, config pra valor que nunca muda, e "manager" que só
guarda referência sem comportamento próprio. Sinal de que falta um objeto/módulo (não mais uma
função): a função fica órfã sem lugar óbvio, ou o arquivo já passou de ~15 funções soltas de
contextos diferentes. Vale para código de domínio e infra.

## Formatação e legibilidade

**No mínimo 2 linhas em branco entre funções** (top-level ou métodos). Não é opcional pra economizar
espaço — é o que separa visualmente onde uma função termina e a próxima começa.

**Dentro de uma função, separe blocos lógicos com uma linha em branco — como se cada bloco fosse um
lote de instruções.** O objetivo é deixar o código "respirar": bloco de validação, bloco de
preparação de dados, bloco de execução, `return` — cada um isolado, mesmo que tecnicamente pudessem
ficar colados.

Ao invés disso:

```python
def funcao() -> None:
    if validacao == "isso":
        coisa = "nao"
        for c in coisa:
            print(c)
        chamar_funcao()
    return aquilo
```

Faça isso:

```python
def funcao() -> None:
    if validacao == "isso":
        coisa = "nao"

        for c in coisa:
            print(c)

        chamar_funcao()

    return aquilo
```

A regra vale em qualquer nível de indentação (dentro de `if`, `for`, `try`, etc.), não só no corpo
raiz da função.

**Guard clause em vez de `if` aninhado.** Mesma lógica da regra de respiro acima: nesting profundo é
o oposto de código legível. Retorne cedo em vez de encaixar o caminho feliz dentro de vários `if`.

Ao invés disso:

```python
def funcao(x) -> None:
    if x:
        if outra_coisa:
            faz_algo()
```

Faça isso:

```python
def funcao(x) -> None:
    if not x:
        return

    if not outra_coisa:
        return

    faz_algo()
```

**Formatação automática não vira regra manual.** `ruff format` já resolve ordenação de import,
espaçamento entre imports e comprimento de linha, e isso é checado em `just check`/CI. Não é
necessário (nem deve virar hábito) revisar isso manualmente — se `just check` está verde, essas
questões já estão resolvidas.

**Docstring só quando a função não é autoexplicativa pelo nome + type hints.** Evite docstring que só
repete o que a assinatura já diz. `def buscar_usuario_por_id(id: str) -> Usuario` não precisa de
`"""Busca o usuário pelo id."""` acima. Reserve docstring para o que a assinatura não deixa claro:
por que a função existe, um efeito colateral não óbvio, uma decisão de design, um caso de borda.

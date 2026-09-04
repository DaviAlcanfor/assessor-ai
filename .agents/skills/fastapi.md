# FastAPI

Duas partes: **práticas oficiais** (do skill oficial do FastAPI, adaptadas ao que este repo faz de
fato) e **pegadinhas deste repo** (achados reais, quase todos vindos de bug já corrigido). Consulte
antes de mexer em `api/`.

## Referências

O conteúdo longo do skill oficial está nos arquivos ao lado, neste mesmo diretório:

| Arquivo | Assunto |
|---|---|
| [dependencies.md](dependencies.md) | `Depends` com `yield`, `scope`, dependência como classe |
| [responses.md](responses.md) | return type vs. `response_model`, status code, headers |
| [streaming.md](streaming.md) | JSON Lines, SSE (`EventSourceResponse`), bytes |
| [path-operations.md](path-operations.md) | roteamento, `APIRouter`, parâmetros de rota |
| [pydantic.md](pydantic.md) | Ellipsis, `RootModel`, validação |
| [other-tools.md](other-tools.md) | uv, Ruff, ty, Asyncer, SQLModel, HTTPX |

Os arquivos oficiais linkam entre si como `references/<arquivo>.md`; aqui todos estão no mesmo
diretório, então o caminho é só `<arquivo>.md`.

## Divergências deliberadas do skill oficial

O skill oficial recomenda algumas coisas que **não** se aplicam aqui. Não "corrija" o repo pra
segui-las sem discutir antes:

- **SQLModel:** o oficial prefere SQLModel a SQLAlchemy. Aqui o Postgres já roda em SQLAlchemy ORM
  (`tools/postgres/models.py`) com migrations versionadas no Alembic. Migrar não traz ganho e
  quebraria o histórico de migration — fica SQLAlchemy. Ver [sqlalchemy.md](sqlalchemy.md).
- **Rotas `async`:** o oficial usa `async def` nos exemplos. Aqui quase todo I/O é síncrono
  (psycopg2, pymongo, redis-py, `fluxo_agentes().invoke`), então rota é `def` normal de propósito —
  ver a seção de pegadinha sobre isso mais abaixo, é regra, não descuido.
- **Asyncer:** não é dependência do projeto. Só faz sentido se aparecer código de fato async (ex.
  streaming SSE) que precise chamar o grafo síncrono — aí sim avalie, não antes.
- **HTTPX:** já é dependência (`httpx`). Em código novo que faça HTTP, use `httpx`, não `requests`.

## `fastapi dev` / `fastapi run`

O entrypoint já está declarado no `pyproject.toml`, então os dois comandos funcionam sem passar
caminho de arquivo:

```toml
[tool.fastapi]
entrypoint = "interfaces.api.main:app"
```

```bash
fastapi dev    # local, com reload
fastapi run    # produção
```

`python main.py api` continua existindo e sobe o mesmo app via `uvicorn.run(..., reload=True)` — é o
caminho usado pelo dispatcher (`main.py`), equivalente ao `fastapi dev` para uso local.

## Usar `Annotated` em dependência e parâmetro

Prefira `Annotated[T, Depends(...)]` / `Annotated[T, Security(...)]` ao valor default. Mantém a
assinatura da função utilizável fora do FastAPI (teste chama direto), respeita o tipo e permite
reaproveitar a dependência como alias.

Do this — alias de tipo reaproveitável, declarado uma vez ao lado da dependência:

```python
# api/auth.py
from typing import Annotated

from fastapi import Depends, Security
from fastapi.security import APIKeyHeader

_api_key_header = APIKeyHeader(name="X-API-Key")


def get_current_user(api_key: Annotated[str, Security(_api_key_header)]) -> str:
    ...


CurrentUserDep = Annotated[str, Depends(get_current_user)]
```

```python
# api/routes/chats.py
@router.post("/{chat_id}/messages")
def send_message(request: Request, chat_id: str, payload: MessageCreate, user_id: CurrentUserDep):
    ...
```

Instead of:

```python
# DO NOT DO THIS
def get_current_user(api_key: str = Security(_api_key_header)) -> str: ...


def send_message(chat_id: str, user_id: str = Depends(get_current_user)): ...
```

> As rotas atuais ainda usam o estilo antigo (`= Depends(...)`) — migração registrada no TODO.md.
> Código novo já nasce com `Annotated`.

## Return type em vez de `response_model` quando são a mesma coisa

Se a rota devolve exatamente o modelo, anote o retorno e apague o `response_model` — a anotação já
valida, filtra, documenta e serializa (com a serialização do Pydantic em Rust).

Do this:

```python
@router.post("", status_code=status.HTTP_201_CREATED)
def create_chat(request: Request, user_id: CurrentUserDep) -> ChatCreateResponse:
    return ChatCreateResponse(chat_id=chat_service.create_chat(user_id))
```

Instead of:

```python
# DO NOT DO THIS — response_model duplicando o que a anotação de retorno já diria
@router.post("", response_model=ChatCreateResponse, status_code=status.HTTP_201_CREATED)
def create_chat(request: Request, user_id=Depends(get_current_user)):
    return ChatCreateResponse(chat_id=...)
```

`response_model` continua certo quando o schema público é **diferente** do que a função retorna (ex.
retornar um model do ORM e expor só alguns campos). Ver [responses.md](responses.md).

## Nada de Ellipsis (`...`) nos schemas

`Field(..., min_length=1)` é forma antiga: campo sem default já é obrigatório.

Do this:

```python
class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=4000)
```

Instead of:

```python
# DO NOT DO THIS
class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=4000)
```

Mesma regra pra `Query()`/`Path()`/`Body()`. E não use `RootModel`: pra body que é lista, anote
`Annotated[list[Item], Body()]` direto. Ver [pydantic.md](pydantic.md).

## Parâmetros no `APIRouter`, não no `include_router()`

`prefix`, `tags` e dependências compartilhadas ficam no próprio router — é o padrão que
`routes/chats.py` e `routes/keys.py` já seguem:

```python
router = APIRouter(prefix="/v1/keys", tags=["keys"], dependencies=[Depends(verify_signup_secret)])
```

`api/app.py` então só faz `app.include_router(keys_router)`, sem repetir configuração.
Uma operação HTTP por função — não misture `GET` e `POST` no mesmo handler.

## Serialização: sem `ORJSONResponse`/`UJSONResponse`

Estão deprecados. A performance vem de declarar o tipo de retorno / `response_model` e deixar o
Pydantic serializar. (`orjson` aparece no `pyproject.toml` só como dependência transitiva do
LangSmith — não é pra usar como response class.)

## Streaming / SSE (quando o streaming da API sair do TODO)

SSE é `response_class=EventSourceResponse` + `yield`:

```python
from fastapi.sse import EventSourceResponse, ServerSentEvent


@router.post("/{chat_id}/messages/stream", response_class=EventSourceResponse)
async def stream_message(...) -> AsyncIterable[ServerSentEvent]:
    yield ServerSentEvent(data={"status": "pensando"}, event="status")
```

**Pegadinha específica daqui:** endpoint SSE é `async` obrigatoriamente, mas `chat_service.send_message`
é síncrono do começo ao fim (grafo LangGraph + psycopg2 + pymongo). Chamar direto dentro do
`async def` trava o event loop inteiro — tem que ir pra thread (`anyio.to_thread.run_sync`), que é
justamente o que o FastAPI faz sozinho hoje por a rota ser `def`. Ver [streaming.md](streaming.md).

## Frontend servido pelo próprio app

Para o frontend planejado no TODO.md, use `app.frontend("/", directory="dist")` em vez de montar
`StaticFiles` na mão — ele entra como rota de baixa prioridade, então as rotas de API continuam
ganhando o match e o fallback de client-side routing funciona.

---

# Pegadinhas deste repo

## Não usar `async def` em rota que chama I/O bloqueante

Se a rota chama SQLAlchemy síncrono, `requests`, ou qualquer lib bloqueante, deixe a rota como
`def` normal. O FastAPI roda `def` num threadpool automaticamente; `async def` roda direto no
event loop — se o corpo bloquear (driver de banco síncrono, chamada HTTP síncrona), trava o loop
inteiro e derruba o throughput de todas as outras requests em andamento, não só a atual.

Do this, `def` síncrono pra código bloqueante (mesmo padrão já usado em `routes/chats.py`):

```python
from fastapi import APIRouter, Depends

router = APIRouter()


@router.post("/{chat_id}/messages")
def send_message(chat_id: str, user_id: str = Depends(get_current_user)):
    return chat_service.send_message(user_id, chat_id, ...)  # SQLAlchemy síncrono por dentro
```

Instead of:

```python
# DO NOT DO THIS
@router.post("/{chat_id}/messages")
async def send_message(chat_id: str, user_id: str = Depends(get_current_user)):
    return chat_service.send_message(user_id, chat_id, ...)  # ainda síncrono, mas agora bloqueia o loop
```

Só use `async def` se o corpo da rota de fato usar bibliotecas async (`asyncpg`, `httpx.AsyncClient`,
etc.) do início ao fim.

## Não deixar `except Exception` genérico engolir `HTTPException`

`HTTPException` também é uma `Exception`. Se uma chamada que pode levantar `HTTPException`
(validação de ownership, outra dependência) fica dentro do mesmo `try` que envolve a lógica de
negócio, o `except Exception` genérico intercepta e transforma um 403/404 legítimo num 500 sem
sentido.

Do this, validação que levanta `HTTPException` fica fora do `try` (mesmo padrão de
`routes/chats.py:_validar_ownership` + `send_message`):

```python
@router.post("/{chat_id}/messages")
def send_message(chat_id: str, user_id: str = Depends(get_current_user)):
    _validar_ownership(chat_id, user_id)  # pode levantar 404/403, fora do try

    try:
        return chat_service.send_message(user_id, chat_id, ...)
    except Exception:
        logger.exception("Falha ao processar mensagem")
        raise HTTPException(500, "Não foi possível processar a mensagem.")
```

Instead of:

```python
# DO NOT DO THIS
@router.post("/{chat_id}/messages")
def send_message(chat_id: str, user_id: str = Depends(get_current_user)):
    try:
        _validar_ownership(chat_id, user_id)  # o 404/403 dela vira 500 aqui
        return chat_service.send_message(user_id, chat_id, ...)
    except Exception:
        raise HTTPException(500, "Não foi possível processar a mensagem.")
```

## `fastapi-guard` (`SecurityMiddleware`): configurar `redis_url` e nunca combinar CORS wildcard com credentials

Dois defaults do `SecurityConfig` que já causaram incidente real neste repo (hoje em `api/middleware.py`):

- Sem `redis_url` explícito, o `fastapi-guard` aponta pro Redis **local** por padrão, não pro Redis
  do projeto. Com `redis_fail_open=False` (o padrão mais seguro), isso derruba toda request com
  `GuardRedisError` em vez de falhar de forma óbvia na configuração.
- `cors_allow_credentials=True` junto de `cors_allow_origins=["*"]` é uma combinação que o próprio
  spec de CORS rejeita (navegador ignora a resposta). Se a API não usa cookie (auth por header, ex.
  `X-API-Key`), `cors_allow_credentials` deve ser `False`.

Do this:

```python
config = SecurityConfig(
    redis_url=settings.REDIS_URL,       # aponta pro Redis real do projeto, não pro local
    enable_cors=True,
    cors_allow_origins=["*"],
    cors_allow_credentials=False,       # sem cookie, sem credentials — combina com wildcard
)
```

Instead of:

```python
# DO NOT DO THIS
config = SecurityConfig(
    enable_cors=True,
    cors_allow_origins=["*"],
    cors_allow_credentials=True,        # inválido com wildcard, e a API não usa cookie mesmo
    # redis_url ausente -> tenta o Redis local, não o do projeto
)
```
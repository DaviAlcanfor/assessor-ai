# FastAPI

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

Dois defaults do `SecurityConfig` que já causaram incidente real neste repo (`interfaces/api/main.py`):

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
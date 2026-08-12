# Redis

## Check-and-set precisa ser atômico: `SET ... NX`, não `EXISTS` + `SET`

`EXISTS` seguido de `SET`/`pipeline.set()` tem uma janela entre as duas chamadas — duas requests
concorrentes podem passar pelo `EXISTS` (nenhuma existe ainda) antes de qualquer uma delas
escrever, furando uma invariante do tipo "só uma key por usuário" (race condition real já
corrigida em `tools/redis/api_key.py`). `SET key value NX=True` faz a checagem e a escrita num
único comando atômico no Redis.

Do this:

```python
def allocate_api_key(user_id: str, api_key: str) -> bool:
    r = get_client()
    if not r.set(_chave_api_key(user_id), _hash_api_key(api_key), ex=TTL, nx=True):
        return False  # já existia — outra request ganhou a corrida
    return True
```

Instead of:

```python
# DO NOT DO THIS
def allocate_api_key(user_id: str, api_key: str) -> bool:
    r = get_client()
    if r.exists(_chave_api_key(user_id)):  # duas requests podem passar aqui juntas
        return False
    r.set(_chave_api_key(user_id), _hash_api_key(api_key), ex=TTL)
    return True
```

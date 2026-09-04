# MongoDB (pymongo)

Pegadinhas reais deste repo. Mongo guarda o histórico de conversa (`graph/tools/chats`) e o perfil
de usuário (`graph/tools/usuarios`). O checkpoint do LangGraph fica no PostgreSQL e é criado pelo
`AsyncPostgresSaver` em `graph/builder.py`; não use `MongoDBSaver` neste projeto.

## `MongoClient` é lazy

`MongoClient(...)` **não** abre socket no construtor — só na primeira operação. É por isso que
`mongo = MongoConn()` no escopo de módulo (`infra/mongo.py`) não viola a regra de "sem I/O no
import" e pode ser importado à vontade.

As conexões compartilhadas ficam em `infra/`; os repositories de domínio ficam em
`graph/tools/<feature>/`. Mantenha a conexão lazy e não crie clientes diretamente dentro de uma
feature.

Do this:

```python
from assessor_ai.infra.mongo import MongoRepo


class ChatsRepo(MongoRepo):
    collection_name = "chats"
```

Instead of:

```python
# DO NOT DO THIS — cria uma conexão própria e mistura infraestrutura com domínio
client = MongoClient(settings.MONGO_URL.get_secret_value())
```

O grafo também é compilado sob demanda em `graph/builder.py`, mas seu checkpointer é
`AsyncPostgresSaver`, não um checkpointer Mongo.

## `ServerSelectionTimeoutError` em deploy = allowlist do Atlas, não código

Já custou dois diagnósticos errados aqui (Python 3.14, TLS handshake — os dois falsos). O sintoma
real do Atlas bloqueando IP é sempre o mesmo:

- erro em **todos** os shards do cluster ao mesmo tempo (`ServerSelectionTimeoutError`, às vezes com
  `TLSV1_ALERT_INTERNAL_ERROR` junto — o alerta de TLS é consequência, não causa)
- funciona local, quebra só no ambiente hospedado
- nada mudou no código de conexão entre o deploy que funcionava e o que quebrou

Antes de mexer em versão de lib, versão de Python ou parâmetro de TLS: **abra o Network Access do
Atlas e confira se o egress do host está liberado.** FastAPI Cloud sai por IP dinâmico, então
allowlist fixa de IP não cobre.

## Histórico curto: `$slice` na projeção, não fatia em Python

O documento de chat acumula todas as mensagens da sessão num array. Buscar o documento inteiro pra
usar as últimas 5 traz o histórico completo pela rede a cada turno.

Do this (`graph/tools/chats/repo.py:buscar`):

```python
return collection.find_one(
    {"session_id": session_id},
    {"messages": {"$slice": -limit}},   # o servidor devolve só as últimas N
)
```

Instead of:

```python
# DO NOT DO THIS
doc = collection.find_one({"session_id": session_id})
doc["messages"] = doc["messages"][-limit:]   # trafegou a conversa inteira à toa
```

## Filtro por `user_id` na query, nunca depois

`buscar` aceita `user_id` opcional e o coloca **no filtro**. Checar dono depois de trazer o
documento é IDOR esperando acontecer — o dado já saiu do banco. Mesma regra das tools de Postgres.

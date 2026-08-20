# MongoDB (pymongo + MongoDBSaver)

Pegadinhas reais deste repo. Mongo guarda três coisas aqui: histórico de conversa
(`tools/mongo/chats`), perfil de usuário (`tools/mongo/users`) e o checkpoint do LangGraph
(`graph/builder.py`).

## `MongoClient` é lazy, `MongoDBSaver` não é

`MongoClient(...)` **não** abre socket no construtor — só na primeira operação. É por isso que
`banco = _conectar()` no escopo de módulo (`tools/mongo/connection.py`) não viola a regra de "sem
I/O no import" e pode ser importado à vontade.

`MongoDBSaver.__init__`, ao contrário, **conecta na hora**: ele cria índices nas collections de
checkpoint. Instanciar no import faria todo `python main.py`, todo `pytest` e toda coleta de teste
baterem no Atlas antes de qualquer coisa acontecer.

Do this — construção adiada pro primeiro uso (`graph/builder.py`):

```python
@cache
def fluxo_agentes():
    checkpointer = MongoDBSaver(banco.client, db_name=banco.name, ...)
    return grafo.compile(checkpointer=checkpointer)
```

Instead of:

```python
# DO NOT DO THIS — conecta no Mongo no import do pacote
checkpointer = MongoDBSaver(banco.client, db_name=banco.name)
fluxo_agentes = grafo.compile(checkpointer=checkpointer)
```

`@cache` (stdlib) já dá o singleton lazy — não escreva memoização na mão com `if _instancia is None`.

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

## O pin `pymongo>=4.12,<4.17` não é decoração

Quem trava o teto é o `langgraph-checkpoint-mongodb` (a versão estável exige `pymongo<4.17`). Subir
o pymongo sem subir o checkpointer quebra o grafo inteiro, não só o Mongo. Se um PR do Dependabot
tentar passar disso, confira a versão do `langgraph-checkpoint-mongodb` antes de mergear.

## Nomear as collections do checkpointer

Os defaults do `MongoDBSaver` colidem com qualquer outro projeto apontando pro mesmo banco. Aqui
elas são explícitas (`graph_checkpoints` / `graph_checkpoint_writes`) — mantenha assim ao mexer no
`fluxo_agentes()`.

## Histórico curto: `$slice` na projeção, não fatia em Python

O documento de chat acumula todas as mensagens da sessão num array. Buscar o documento inteiro pra
usar as últimas 5 traz o histórico completo pela rede a cada turno.

Do this (`tools/mongo/chats/core.py:buscar`):

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

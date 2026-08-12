# LangChain / LangGraph

## Usar `response_format` em vez de parsear texto livre com regex

Se um nó espera uma decisão estruturada do LLM (rota, categoria, campo extraído), não peça pro
prompt devolver um formato tipo `ROUTE=financeiro` e depois cace isso com regex na resposta — o
LLM pode variar o formato e o regex silenciosamente cai no fallback errado. `create_agent` aceita
um `response_format` (Pydantic model) e já resolve isso dentro do próprio loop do agente (via
tool-calling ou structured output nativo do provider, sem chamada extra de LLM), devolvendo o
resultado tipado em `result["structured_response"]`.

Do this:

```python
from pydantic import BaseModel
from langchain.agents import create_agent


class Roteamento(BaseModel):
    rota: Route
    pergunta_original: str


router_app = create_agent(
    model=llm_rapido,
    system_prompt=RouterPrompts.system_prompt(),
    response_format=Roteamento,
)

saida = router_app.invoke({"messages": list(estado["messages"])})
roteamento = saida["structured_response"]  # já é um Roteamento, sem parsing manual
```

Instead of:

```python
# DO NOT DO THIS
saida = router_app.invoke({"messages": list(estado["messages"])})
texto = saida["messages"][-1].content
match = re.search(r"ROUTE=(\w+)", texto)  # quebra se o LLM variar o formato
rota = Route(match.group(1)) if match else Route.FIM
```

## Reducer explícito em toda lista/dict acumulado no `State`

Campo de `State` do LangGraph sem `Annotated[..., reducer]` é sobrescrito a cada nó que retorna
essa chave, não mesclado — o padrão do LangGraph é "last write wins". Listas que crescem entre nós
(histórico, agentes chamados) precisam de reducer explícito (`operator.add`, ou `add_messages` pra
mensagens, que também deduplica por id e faz merge de chunks). Mesmo padrão já usado em
`graph/state.py`.

Do this:

```python
import operator
from typing import Annotated

from langgraph.graph import MessagesState


class Estado(MessagesState):  # messages já vem com add_messages embutido
    agentes_chamados: Annotated[list[str], operator.add]
```

Instead of:

```python
# DO NOT DO THIS
class Estado(MessagesState):
    agentes_chamados: list[str]  # cada nó que retorna isso PISA no valor anterior, não acumula
```
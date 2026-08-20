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
## `system_prompt` de `create_agent` congela no import — contexto dinâmico vai por mensagem

`create_agent(..., system_prompt=X.system_prompt())` avalia a string **uma vez**, quando o módulo é
importado (`graph/agents.py` roda no import). Qualquer coisa que mude com o tempo embutida ali fica
congelada pelo tempo de vida do processo: data/hora, perfil do usuário, contexto do turno. No
terminal e na TUI passa despercebido porque reiniciam a cada uso — a API fica dias com o mesmo
valor. Já aconteceu aqui com o bloco de data (a API interpretava "hoje" como a data do deploy).

Do this — o que muda por turno entra como mensagem de sistema no `invoke` (ver
`agents/nodes/contexto.py`):

```python
mensagens = [{"role": "system", "content": contexto_do_turno(perfil, pergunta)}, *estado["messages"]]
saida = financeiro_app.invoke({"messages": mensagens})
```

Instead of:

```python
# DO NOT DO THIS — a data é a do import, não a de agora
class GenericAgent:
    CONTEXTO_TEMPORAL = f"Data atual: {datetime.now()}"   # roda uma vez, no import do módulo
```

Duas system messages na mesma lista é seguro nos dois providers do projeto: Groq é
OpenAI-compatible e aceita várias; o `langchain-google-genai` **funde** as system messages extras no
mesmo `system_instruction` (verificado em `_parse_chat_history` — vira uma segunda `part`, não um
erro). **Ressalva:** essa fusão só acontece se já houver uma system message no índice 0 — se não houver,
o `langchain-google-genai` **descarta a segunda em silêncio** (`else: pass` no mesmo trecho), sem
erro nem warning. Hoje é seguro porque todo agente é criado com `system_prompt`, que o
`create_agent` prepende (`langchain/agents/factory.py`: `messages = [request.system_message,
*messages]`). Agente sem `system_prompt` + contexto por mensagem = contexto perdido sem aviso.

Alternativa mais formal, se um dia precisar do prompt inteiro dinâmico: o middleware
`dynamic_prompt` do `langchain.agents.middleware`, que recalcula o system prompt a cada chamada de
modelo.

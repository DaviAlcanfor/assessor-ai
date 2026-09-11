"""
Eventos da timeline de execução do agente, pra streaming via SSE
(`POST /v1/chats/{chat_id}/messages/stream`, ver `api/routes/chats.py`).

Nunca carregam prompt, estado interno do grafo, argumento de tool ou conteúdo cru de LLM — só
identidade de node e a resposta final já revisada. Quem produz esses eventos é
`services/runner.py:executar_stream`.

Sem streaming de token da resposta final: o texto só fica seguro pra mostrar depois que o
`guardrail_saida` termina (revisão de compliance + redação de PII), e essas duas etapas operam
sobre o texto inteiro — não dá pra revisar/redigir em fragmentos parciais sem risco de cortar um
token de PII no meio. Por isso `AnswerReady` chega inteira, não como uma sequência de deltas.
"""

from typing import Annotated, Literal

from pydantic import BaseModel, Field

from assessor_ai.graph.agents.nodes.names import NodeName
from assessor_ai.graph.state import Route


class RunStarted(BaseModel):
    type: Literal["run_started"] = "run_started"


class NodeStarted(BaseModel):
    type: Literal["node_started"] = "node_started"
    node: NodeName


class RouteSelected(BaseModel):
    type: Literal["route_selected"] = "route_selected"
    route: Route


class NodeFinished(BaseModel):
    type: Literal["node_finished"] = "node_finished"
    node: NodeName


class AnswerReady(BaseModel):
    type: Literal["answer_ready"] = "answer_ready"
    content: str


class RunFinished(BaseModel):
    type: Literal["run_finished"] = "run_finished"


class RunFailed(BaseModel):
    type: Literal["run_failed"] = "run_failed"
    message: str


ExecutionEvent = Annotated[
    RunStarted
    | NodeStarted
    | RouteSelected
    | NodeFinished
    | AnswerReady
    | RunFinished
    | RunFailed,
    Field(discriminator="type"),
]


__all__ = [
    "AnswerReady",
    "ExecutionEvent",
    "NodeFinished",
    "NodeStarted",
    "RouteSelected",
    "RunFailed",
    "RunFinished",
    "RunStarted",
]

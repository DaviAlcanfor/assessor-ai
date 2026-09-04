import operator
from enum import StrEnum
from typing import Annotated, NotRequired, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph import MessagesState

from assessor_ai.graph.agents.nodes.names import NodeName
from assessor_ai.privacy import MapaPII


class Route(StrEnum):
    FINANCEIRO =      "financeiro"
    AGENDA            = "agenda"
    FAQ               = "faq"
    FIM               = "fim"
    GUARDRAIL_ENTRADA = "guardrail_entrada"
    GUARDRAIL_SAIDA   = "guardrail_saida"


class Estado(MessagesState):
    resposta_especialista: NotRequired[str]
    agentes_chamados:      NotRequired[Annotated[list[NodeName], operator.add]]
    rota:                  NotRequired[Route]
    pergunta_original:     NotRequired[str]
    mapa_pii:              NotRequired[MapaPII]
    mensagem_bloqueada:    NotRequired[str | None]
    perfil_usuario:        NotRequired[str]


class EstadoUpdate(TypedDict, total=False):
    messages: list[AnyMessage | dict[str, str]]
    resposta_especialista: str
    agentes_chamados: list[NodeName]
    rota: Route
    pergunta_original: str
    mapa_pii: MapaPII
    mensagem_bloqueada: str | None
    perfil_usuario: str
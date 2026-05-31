import operator
from typing import Annotated
from langgraph.graph import MessagesState
from enum import StrEnum


class Route(StrEnum):
    FINANCEIRO = "financeiro"
    AGENDA     = "agenda"
    FAQ        = "faq"
    FIM        = "fim"


class Estado(MessagesState):
    resposta_especialista: str
    agentes_chamados:      Annotated[list[str], operator.add]
    rota:                  Route
    pergunta_original:     str                             

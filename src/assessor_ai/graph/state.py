import operator
from collections.abc import Awaitable, Callable
from enum import StrEnum
from typing import Annotated, NotRequired, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph import MessagesState

from assessor_ai.graph.agents.nodes.names import NodeName
from assessor_ai.privacy import MapaPII


class Route(StrEnum):
    """Rotas que o roteador pode escolher. Guardrails/orquestrador são NodeName, não Route."""

    FINANCEIRO = "financeiro"
    AGENDA = "agenda"
    FAQ = "faq"
    FIM = "fim"


class EntradaGrafo(MessagesState):
    """Único formato aceito ao iniciar um turno — impede injetar campos internos do estado."""

    perfil_usuario: NotRequired[str]


class Estado(MessagesState):
    resposta_especialista: NotRequired[str]
    agentes_chamados: NotRequired[Annotated[list[NodeName], operator.add]]
    rota: NotRequired[Route]
    pergunta_original: NotRequired[str]
    mapa_pii: NotRequired[MapaPII]
    mensagem_bloqueada: NotRequired[str | None]
    perfil_usuario: NotRequired[str]


class SaidaGrafo(MessagesState):
    """Único formato devolvido ao chamador — não expõe mapa_pii, perfil, rota etc."""


class RouterUpdate(TypedDict):
    agentes_chamados: list[NodeName]
    rota: Route
    pergunta_original: str
    messages: NotRequired[list[AnyMessage]]


class EspecialistaUpdate(TypedDict):
    agentes_chamados: list[NodeName]
    resposta_especialista: str


class FaqUpdate(TypedDict):
    agentes_chamados: list[NodeName]
    messages: list[AnyMessage]
    resposta_especialista: str


class OrquestradorUpdate(TypedDict):
    agentes_chamados: list[NodeName]
    messages: list[AnyMessage]
    resposta_especialista: str


class GuardrailEntradaUpdate(TypedDict):
    agentes_chamados: list[NodeName]
    messages: list[AnyMessage]
    mensagem_bloqueada: str | None
    mapa_pii: NotRequired[MapaPII]


class GuardrailSaidaUpdate(TypedDict):
    agentes_chamados: list[NodeName]
    messages: list[AnyMessage]


# Contrato dos nodes: `Estado -> Awaitable[R]`, R sendo o Update específico de cada node
# (RouterUpdate, EspecialistaUpdate, ...). Não é Protocol de propósito — os nodes de hoje são
# funções puras, sem atributo/método extra que justifique uma classe; Protocol só valeria a pena
# se algum node precisasse carregar estado ou metadado além da própria chamada. Usado em
# `graph/builder.py` pra travar, com mypy, que cada função passada a `add_node()` bate com o
# Update esperado naquele node — sem isso, um builder que troca `no_roteador` por `no_financeiro`
# por engano ainda tipa limpo, porque `add_node()` é permissivo demais nos stubs do LangGraph.
type AsyncNode[R] = Callable[[Estado], Awaitable[R]]

import os
os.environ["LANGGRAPH_ALLOWED_MSGPACK_MODULES"] = (
    "agents.nodes.names,graph.state"
)

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from graph.state import Estado, Route

from agents.nodes.names import NodeName
from agents.nodes import (
    no_roteador,
    no_orquestrador,
    no_financeiro,
    no_agenda,
    no_faq,
    no_guardrail_entrada,
    no_guardrail_saida,
)


def decidir_apos_guardrail_entrada(estado: Estado) -> str:
    if estado.get("mensagem_bloqueada"):
        return Route.FIM
    return NodeName.ROTEADOR


def decidir_especialista(estado: Estado) -> str:
    rota = estado.get("rota", Route.FIM)
    if rota not in (Route.FINANCEIRO, Route.AGENDA, Route.FAQ):
        return Route.FIM
    return rota


grafo = StateGraph(Estado)

grafo.add_node(NodeName.GUARDRAIL_ENTRADA, no_guardrail_entrada)
grafo.add_node(NodeName.ROTEADOR,          no_roteador)
grafo.add_node(NodeName.FINANCEIRO,        no_financeiro)
grafo.add_node(NodeName.AGENDA,            no_agenda)
grafo.add_node(NodeName.FAQ,               no_faq)
grafo.add_node(NodeName.ORQUESTRADOR,      no_orquestrador)
grafo.add_node(NodeName.GUARDRAIL_SAIDA,   no_guardrail_saida)


grafo.set_entry_point(NodeName.GUARDRAIL_ENTRADA)

grafo.add_conditional_edges(
    source   = NodeName.GUARDRAIL_ENTRADA,
    path     = decidir_apos_guardrail_entrada,
    path_map = {
        Route.FIM:         END,
        NodeName.ROTEADOR: NodeName.ROTEADOR,
    },
)

grafo.add_conditional_edges(
    source   = NodeName.ROTEADOR,
    path     = decidir_especialista,
    path_map = {
        Route.FINANCEIRO: NodeName.FINANCEIRO,
        Route.AGENDA:     NodeName.AGENDA,
        Route.FAQ:        NodeName.FAQ,
        Route.FIM:        END,
    },
)

grafo.add_edge(NodeName.FINANCEIRO,   NodeName.ORQUESTRADOR)
grafo.add_edge(NodeName.AGENDA,       NodeName.ORQUESTRADOR)
grafo.add_edge(NodeName.ORQUESTRADOR, NodeName.GUARDRAIL_SAIDA)
grafo.add_edge(NodeName.FAQ,          NodeName.GUARDRAIL_SAIDA)
grafo.add_edge(NodeName.GUARDRAIL_SAIDA, END)


memory = MemorySaver()
fluxo_agentes = grafo.compile(checkpointer=memory)

__all__ = ["fluxo_agentes"]
import os
os.environ["LANGGRAPH_ALLOWED_MSGPACK_MODULES"] = (
    "agents.nodes.names,graph.state"
)

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from graph.state import Estado, Route
from graph.agents import faq_app

from agents.nodes.names import NodeName
from agents.nodes import (
    no_roteador,
    no_orquestrador,
    no_financeiro,
    no_agenda,
    no_faq,
)


def decidir_especialista(estado: Estado) -> str:
    """
    Lê a rota já parseada por no_roteador e devolve o nome do próximo nó.
    """
    
    rota = estado.get("rota", Route.FIM)
    
    if not rota in (Route.FINANCEIRO,Route.AGENDA, Route.FAQ):
        return Route.FIM
    
    return rota 


grafo = StateGraph(Estado)

grafo.add_node(NodeName.ROTEADOR,     no_roteador)
grafo.add_node(NodeName.FINANCEIRO,   no_financeiro)
grafo.add_node(NodeName.AGENDA,       no_agenda)
grafo.add_node(NodeName.FAQ,          no_faq)
grafo.add_node(NodeName.ORQUESTRADOR, no_orquestrador)

grafo.set_entry_point(NodeName.ROTEADOR)

grafo.add_conditional_edges(
    source = NodeName.ROTEADOR,    
    path =   decidir_especialista,  
    path_map = {
        Route.FINANCEIRO: NodeName.FINANCEIRO,
        Route.AGENDA:     NodeName.AGENDA,
        Route.FAQ:        NodeName.FAQ,
        Route.FIM:        END,       
    },
)

grafo.add_edge(NodeName.FINANCEIRO, NodeName.ORQUESTRADOR)
grafo.add_edge(NodeName.AGENDA,     NodeName.ORQUESTRADOR)
grafo.add_edge(NodeName.ORQUESTRADOR, END)
grafo.add_edge(NodeName.FAQ,          END)   # FAQ bypassa o orquestrador


memory = MemorySaver()
fluxo_agentes = grafo.compile(checkpointer=memory)

__all__ = ["fluxo_agentes"]
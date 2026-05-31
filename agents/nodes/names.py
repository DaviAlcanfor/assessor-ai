from enum import StrEnum


class NodeName(StrEnum):
    ROTEADOR =     "roteador_node"
    FINANCEIRO =   "financeiro_node"
    AGENDA =       "agenda_node"
    FAQ =          "faq_node"
    ORQUESTRADOR = "orquestrador_node"


__all__ = ["NodeName"]
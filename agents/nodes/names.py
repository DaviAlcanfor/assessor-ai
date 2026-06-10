from enum import StrEnum


class NodeName(StrEnum):
    ROTEADOR =     "roteador_node"
    FINANCEIRO =   "financeiro_node"
    AGENDA =       "agenda_node"
    FAQ =          "faq_node"
    ORQUESTRADOR = "orquestrador_node"
    GUARDRAIL_ENTRADA = "guardrail_entrada_node"
    GUARDRAIL_SAIDA = "guardrail_saida_node"


__all__ = ["NodeName"]
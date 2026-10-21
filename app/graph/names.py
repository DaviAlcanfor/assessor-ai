from typing import Literal

type NodeName = Literal[
    "roteador_node",
    "financeiro_node",
    "agenda_node",
    "faq_node",
    "orquestrador_node",
    "guardrail_entrada_node",
    "guardrail_saida_node",
]


ROTEADOR: NodeName = "roteador_node"
FINANCEIRO: NodeName = "financeiro_node"
AGENDA: NodeName = "agenda_node"
FAQ: NodeName = "faq_node"
ORQUESTRADOR: NodeName = "orquestrador_node"
GUARDRAIL_ENTRADA: NodeName = "guardrail_entrada_node"
GUARDRAIL_SAIDA: NodeName = "guardrail_saida_node"


__all__ = [
    "AGENDA",
    "FAQ",
    "FINANCEIRO",
    "GUARDRAIL_ENTRADA",
    "GUARDRAIL_SAIDA",
    "ORQUESTRADOR",
    "ROTEADOR",
]
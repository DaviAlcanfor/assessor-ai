"""
Contexto por turno para os agentes compilados.

`perfil_usuario` e `pergunta_original` vivem no Estado do grafo, mas os agentes
(`graph/agents.py`) são compilados no import com system_prompt fixo — sem isso o
especialista nunca enxerga nem o perfil nem a pergunta que o roteador encaminhou.
"""

from assessor_ai.agents.prompts.base import contexto_do_turno
from assessor_ai.graph.state import Estado


def mensagens_com_contexto(estado: Estado, incluir_pergunta: bool = True) -> list:
    """
    Histórico do turno precedido de uma mensagem de sistema com data/hora atual,
    perfil do usuário e (opcionalmente) a pergunta encaminhada pelo roteador.
    """

    contexto = contexto_do_turno(
        perfil_usuario=estado.get("perfil_usuario", ""),
        pergunta_original=estado.get("pergunta_original", "") if incluir_pergunta else "",
    )

    return [{"role": "system", "content": contexto}, *estado["messages"]]


__all__ = ["mensagens_com_contexto"]

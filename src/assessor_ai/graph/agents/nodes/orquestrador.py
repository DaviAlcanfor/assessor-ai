from langchain_core.messages import AIMessage, HumanMessage

from assessor_ai.graph.agents import orquestrador_app
from assessor_ai.graph.agents.nodes.contexto import mensagens_com_contexto, responder
from assessor_ai.graph.agents.nodes.names import ORQUESTRADOR
from assessor_ai.graph.state import Estado, EstadoUpdate


async def no_orquestrador(estado: Estado) -> EstadoUpdate:
    mensagens = mensagens_com_contexto(estado, incluir_pergunta=False) + [
        HumanMessage(content=estado["resposta_especialista"])
    ]

    resposta = await responder(orquestrador_app, mensagens)

    return EstadoUpdate(
        agentes_chamados=[ORQUESTRADOR],
        messages=[AIMessage(content=resposta)],
        resposta_especialista=resposta,
    )


__all__ = ['no_orquestrador']

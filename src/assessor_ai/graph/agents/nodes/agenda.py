from assessor_ai.graph.agents import agenda_app
from assessor_ai.graph.agents.nodes.contexto import mensagens_com_contexto
from assessor_ai.graph.agents.nodes.names import AGENDA
from assessor_ai.graph.state import Estado, EstadoUpdate


async def no_agenda(estado: Estado) -> EstadoUpdate:

    saida = await agenda_app.ainvoke({"messages": mensagens_com_contexto(estado)})
    resposta = saida["messages"][-1].content

    return EstadoUpdate(
        agentes_chamados=[AGENDA],
        resposta_especialista=resposta,
    )


__all__ = ['no_agenda']

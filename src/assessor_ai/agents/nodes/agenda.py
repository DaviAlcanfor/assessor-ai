from assessor_ai.agents.nodes.contexto import mensagens_com_contexto
from assessor_ai.agents.nodes.names import NodeName
from assessor_ai.graph.agents import agenda_app
from assessor_ai.graph.state import Estado


async def no_agenda(estado: Estado) -> dict:

    saida = await agenda_app.ainvoke({"messages": mensagens_com_contexto(estado)})
    resposta = saida["messages"][-1].content

    return {
        "agentes_chamados":      [NodeName.AGENDA],
        "resposta_especialista": resposta,
    }


__all__ = ['no_agenda']

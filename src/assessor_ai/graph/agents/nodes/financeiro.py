from assessor_ai.graph.agents import financeiro_app
from assessor_ai.graph.agents.nodes.contexto import mensagens_com_contexto
from assessor_ai.graph.agents.nodes.names import FINANCEIRO
from assessor_ai.graph.state import Estado, EstadoUpdate


async def no_financeiro(estado: Estado) -> EstadoUpdate:

    saida = await financeiro_app.ainvoke({"messages": mensagens_com_contexto(estado)})
    resposta = saida["messages"][-1].content

    return EstadoUpdate(
        agentes_chamados=[FINANCEIRO],
        resposta_especialista=resposta,
    )


__all__ = ['no_financeiro']

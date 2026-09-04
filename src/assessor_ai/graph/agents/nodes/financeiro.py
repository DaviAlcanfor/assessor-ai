from assessor_ai.graph.agents import financeiro_app
from assessor_ai.graph.agents.nodes.contexto import mensagens_com_contexto
from assessor_ai.graph.agents.nodes.names import NodeName
from assessor_ai.graph.state import Estado


async def no_financeiro(estado: Estado) -> dict:

    saida = await financeiro_app.ainvoke({"messages": mensagens_com_contexto(estado)})
    resposta = saida["messages"][-1].content

    return {
        "agentes_chamados":      [NodeName.FINANCEIRO],
        "resposta_especialista": resposta,
    }


__all__ = ['no_financeiro']

from assessor_ai.agents.nodes.names import NodeName
from assessor_ai.graph.agents import financeiro_app
from assessor_ai.graph.state import Estado


def no_financeiro(estado: Estado) -> dict:

    saida = financeiro_app.invoke({"messages": list(estado["messages"])})
    resposta = saida["messages"][-1].content

    return {
        "agentes_chamados":      [NodeName.FINANCEIRO],
        "resposta_especialista": resposta,
    }


__all__ = ['no_financeiro']
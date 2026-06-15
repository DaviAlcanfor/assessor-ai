from graph.state import Estado
from graph.agents import financeiro_app
from agents.nodes.names import NodeName


def no_financeiro(estado: Estado) -> dict:

    saida = financeiro_app.invoke({"messages": list(estado["messages"])})
    resposta = saida["messages"][-1].content

    return {
        "agentes_chamados":      [NodeName.FINANCEIRO],
        "resposta_especialista": resposta,
    }


__all__ = ['no_financeiro']
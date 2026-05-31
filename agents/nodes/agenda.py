from graph.state import Estado
from graph.agents import agenda_app
from agents.nodes.names import NodeName


def no_agenda(estado: Estado) -> dict:

    saida = agenda_app.invoke({"messages": list(estado["messages"])})
    resposta = saida["messages"][-1].content

    return {
        "agentes_chamados":    [NodeName.AGENDA],
        "resposta_especialista": resposta,
    }
    

__all__ = ['no_agenda']
from graph.state import Estado
from graph.agents import faq_app
from agents.nodes.names import NodeName


def no_faq(estado: Estado) -> dict:

    saida = faq_app.invoke({
        "messages": [{"role": "human", "content": estado["pergunta_original"]}]
    })
    resposta = saida["messages"][-1].content

    return {
        "agentes_chamados":      [NodeName.FAQ],
        "messages":              [{"role": "assistant", "content": resposta}],
        "resposta_especialista": resposta,
    }
    
    
__all__ = ['no_faq']
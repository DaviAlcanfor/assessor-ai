from graph.state import Estado
from graph.agents import orquestrador_app


def no_orquestrador(estado: Estado) -> dict:

    saida = orquestrador_app.invoke({
        "messages": [
            {"role": "human", "content": estado["resposta_especialista"]}
        ]
    })

    return {
        "agentes_chamados": [estado["rota"], "orquestrador"],
        "messages":         [{"role": "assistant", "content": saida["messages"][-1].content}],
    }
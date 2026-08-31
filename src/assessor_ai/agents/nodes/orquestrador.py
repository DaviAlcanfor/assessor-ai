from assessor_ai.agents.nodes.contexto import mensagens_com_contexto
from assessor_ai.agents.nodes.names import NodeName
from assessor_ai.graph.agents import orquestrador_app
from assessor_ai.graph.state import Estado


async def no_orquestrador(estado: Estado) -> dict:

    mensagens = mensagens_com_contexto(estado, incluir_pergunta=False) + [
        {"role": "human", "content": estado["resposta_especialista"]}
    ]

    saida = await orquestrador_app.ainvoke({"messages": mensagens})

    return {
        "agentes_chamados":      [NodeName.ORQUESTRADOR],
        "messages":              [{"role": "assistant", "content": saida["messages"][-1].content}],
        "resposta_especialista": saida["messages"][-1].content,
    }


__all__ = ['no_orquestrador']

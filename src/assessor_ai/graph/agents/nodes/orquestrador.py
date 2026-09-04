from assessor_ai.graph.agents import orquestrador_app
from assessor_ai.graph.agents.nodes.contexto import mensagens_com_contexto
from assessor_ai.graph.agents.nodes.names import ORQUESTRADOR
from assessor_ai.graph.state import Estado, EstadoUpdate


async def no_orquestrador(estado: Estado) -> EstadoUpdate:

    mensagens = mensagens_com_contexto(estado, incluir_pergunta=False) + [
        {"role": "human", "content": estado["resposta_especialista"]}
    ]

    saida = await orquestrador_app.ainvoke({"messages": mensagens})

    return EstadoUpdate(
        agentes_chamados=[ORQUESTRADOR],
        messages=[{"role": "assistant", "content": saida["messages"][-1].content}],
        resposta_especialista=saida["messages"][-1].content,
    )


__all__ = ['no_orquestrador']

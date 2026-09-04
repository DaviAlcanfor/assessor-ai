from assessor_ai.graph.agents import faq_app
from assessor_ai.graph.agents.nodes.names import FAQ
from assessor_ai.graph.agents.prompts.loader import contexto_do_turno
from assessor_ai.graph.state import Estado, EstadoUpdate


async def no_faq(estado: Estado) -> EstadoUpdate:

    saida = await faq_app.ainvoke({
        "messages": [
            {"role": "system", "content": contexto_do_turno(estado.get("perfil_usuario", ""))},
            {"role": "human", "content": estado["pergunta_original"]},
        ]
    })
    resposta = saida["messages"][-1].content

    return EstadoUpdate(
        agentes_chamados=[FAQ],
        messages=[{"role": "assistant", "content": resposta}],
        resposta_especialista=resposta,
    )


__all__ = ['no_faq']

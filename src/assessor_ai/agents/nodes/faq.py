from assessor_ai.agents.nodes.names import NodeName
from assessor_ai.core.prompts.loader import contexto_do_turno
from assessor_ai.graph.agents import faq_app
from assessor_ai.graph.state import Estado


async def no_faq(estado: Estado) -> dict:

    saida = await faq_app.ainvoke({
        "messages": [
            {"role": "system", "content": contexto_do_turno(estado.get("perfil_usuario", ""))},
            {"role": "human", "content": estado["pergunta_original"]},
        ]
    })
    resposta = saida["messages"][-1].content

    return {
        "agentes_chamados":      [NodeName.FAQ],
        "messages":              [{"role": "assistant", "content": resposta}],
        "resposta_especialista": resposta,
    }


__all__ = ['no_faq']

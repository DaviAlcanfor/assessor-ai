from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from assessor_ai.graph.agents import faq_app
from assessor_ai.graph.agents.nodes.contexto import responder
from assessor_ai.graph.agents.nodes.names import FAQ
from assessor_ai.graph.agents.prompts.loader import contexto_do_turno
from assessor_ai.graph.state import Estado, EstadoUpdate


async def no_faq(estado: Estado) -> EstadoUpdate:
    resposta = await responder(
        faq_app,
        [
            SystemMessage(content=contexto_do_turno(estado.get("perfil_usuario", ""))),
            HumanMessage(content=estado["pergunta_original"]),
        ],
    )

    return EstadoUpdate(
        agentes_chamados=[FAQ],
        messages=[AIMessage(content=resposta)],
        resposta_especialista=resposta,
    )


__all__ = ['no_faq']

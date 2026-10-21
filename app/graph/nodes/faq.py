from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.graph.agents import faq_app
from app.graph.names import FAQ
from app.graph.nodes.contexto import responder
from app.graph.prompts.loader import contexto_do_turno
from app.graph.state import Estado, FaqUpdate
from app.telemetry import medir_node


@medir_node(FAQ)
async def no_faq(estado: Estado) -> FaqUpdate:
    resposta = await responder(
        faq_app,
        [
            SystemMessage(content=contexto_do_turno(estado.get("perfil_usuario", ""))),
            HumanMessage(content=estado["pergunta_original"]),
        ],
    )

    return FaqUpdate(
        agentes_chamados=[FAQ],
        messages=[AIMessage(content=resposta)],
        resposta_especialista=resposta,
    )


__all__ = ['no_faq']

from langchain_core.messages import HumanMessage

from app.graph.agents import orquestrador_app
from app.graph.names import ORQUESTRADOR
from app.graph.nodes.contexto import mensagens_com_contexto, responder
from app.graph.state import Estado, OrquestradorUpdate
from app.telemetry import medir_node


@medir_node(ORQUESTRADOR)
async def no_orquestrador(estado: Estado) -> OrquestradorUpdate:
    mensagens = mensagens_com_contexto(estado, incluir_pergunta=False) + [
        HumanMessage(content=estado["resposta_especialista"])
    ]

    resposta = await responder(orquestrador_app, mensagens)

    # A frase só vira mensagem do chat depois do juiz: publicar aqui deixaria no histórico do
    # checkpoint uma resposta que o juiz ainda pode recusar.
    return OrquestradorUpdate(
        agentes_chamados=[ORQUESTRADOR],
        resposta_especialista=resposta,
    )


__all__ = ['no_orquestrador']

from assessor_ai.graph.agents import agenda_app
from assessor_ai.graph.agents.nodes.contexto import mensagens_com_contexto, responder
from assessor_ai.graph.agents.nodes.names import AGENDA
from assessor_ai.graph.state import EspecialistaUpdate, Estado
from assessor_ai.metrics import medir_node


@medir_node(AGENDA)
async def no_agenda(estado: Estado) -> EspecialistaUpdate:
    resposta = await responder(agenda_app, mensagens_com_contexto(estado))

    return EspecialistaUpdate(
        agentes_chamados=[AGENDA],
        resposta_especialista=resposta,
    )


__all__ = ['no_agenda']

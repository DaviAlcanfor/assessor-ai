from app.graph.agents import agenda_app
from app.graph.names import AGENDA
from app.graph.nodes.contexto import mensagens_com_contexto, responder_com_evidencias
from app.graph.state import EspecialistaUpdate, Estado
from app.telemetry import medir_node


@medir_node(AGENDA)
async def no_agenda(estado: Estado) -> EspecialistaUpdate:
    resposta, evidencias = await responder_com_evidencias(agenda_app, mensagens_com_contexto(estado))

    return EspecialistaUpdate(
        agentes_chamados=[AGENDA],
        resposta_especialista=resposta,
        dados_especialista=evidencias,
    )


__all__ = ['no_agenda']

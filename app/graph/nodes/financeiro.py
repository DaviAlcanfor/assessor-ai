from app.graph.agents import financeiro_app
from app.graph.names import FINANCEIRO
from app.graph.nodes.contexto import mensagens_com_contexto, responder_com_evidencias
from app.graph.state import EspecialistaUpdate, Estado
from app.telemetry import medir_node


@medir_node(FINANCEIRO)
async def no_financeiro(estado: Estado) -> EspecialistaUpdate:
    resposta, evidencias = await responder_com_evidencias(financeiro_app, mensagens_com_contexto(estado))

    return EspecialistaUpdate(
        agentes_chamados=[FINANCEIRO],
        resposta_especialista=resposta,
        dados_especialista=evidencias,
    )


__all__ = ['no_financeiro']

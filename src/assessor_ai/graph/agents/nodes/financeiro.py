from assessor_ai.graph.agents import financeiro_app
from assessor_ai.graph.agents.nodes.contexto import mensagens_com_contexto, responder
from assessor_ai.graph.agents.nodes.names import FINANCEIRO
from assessor_ai.graph.state import EspecialistaUpdate, Estado
from assessor_ai.metrics import medir_node


@medir_node(FINANCEIRO)
async def no_financeiro(estado: Estado) -> EspecialistaUpdate:
    resposta = await responder(financeiro_app, mensagens_com_contexto(estado))

    return EspecialistaUpdate(
        agentes_chamados=[FINANCEIRO],
        resposta_especialista=resposta,
    )


__all__ = ['no_financeiro']

from assessor_ai.graph.agents import financeiro_app
from assessor_ai.graph.agents.nodes.contexto import mensagens_com_contexto, responder
from assessor_ai.graph.agents.nodes.names import FINANCEIRO
from assessor_ai.graph.state import Estado, EstadoUpdate


async def no_financeiro(estado: Estado) -> EstadoUpdate:
    resposta = await responder(financeiro_app, mensagens_com_contexto(estado))

    return EstadoUpdate(
        agentes_chamados=[FINANCEIRO],
        resposta_especialista=resposta,
    )


__all__ = ['no_financeiro']

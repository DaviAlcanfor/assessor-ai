import re

from langchain_core.messages import AIMessage

from assessor_ai.graph.agents import router_app
from assessor_ai.graph.agents.nodes.contexto import mensagens_com_contexto, responder
from assessor_ai.graph.agents.nodes.names import ROTEADOR
from assessor_ai.graph.state import Estado, Route, RouterUpdate
from assessor_ai.logging import get_logger
from assessor_ai.metrics import ROUTER_DECISIONS, medir_node

log = get_logger(__name__)


def _extrair_rota(texto: str) -> Route:

    match = re.search(r"ROUTE=(\w+)", texto)
    if not match:
        return Route.FIM
    
    try:
        return Route(match.group(1))
    except ValueError:
        return Route.FIM


def _extrair_pergunta(texto: str) -> str:

    match = re.search(r"PERGUNTA_ORIGINAL=(.+)", texto)
    if not match:
        return ""

    return match.group(1).strip()


@medir_node(ROTEADOR)
async def no_roteador(estado: Estado) -> RouterUpdate:

    texto = await responder(router_app, mensagens_com_contexto(estado, incluir_pergunta=False))
    rota  = _extrair_rota(texto)
    pergunta = _extrair_pergunta(texto)

    log.debug(f"Rota escolhida: {rota} | pergunta: '{pergunta}'")
    ROUTER_DECISIONS.labels(route=rota.value).inc()

    if rota is Route.FIM:
        return RouterUpdate(
            agentes_chamados=[ROTEADOR],
            rota=Route.FIM,
            pergunta_original=pergunta,
            messages=[AIMessage(content=texto)],
        )

    return RouterUpdate(
        agentes_chamados=[ROTEADOR],
        rota=rota,
        pergunta_original=pergunta,
    )
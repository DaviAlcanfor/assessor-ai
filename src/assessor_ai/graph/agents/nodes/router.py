import re

from assessor_ai.graph.agents import router_app
from assessor_ai.graph.agents.nodes.contexto import mensagens_com_contexto
from assessor_ai.graph.agents.nodes.names import ROTEADOR
from assessor_ai.graph.state import Estado, EstadoUpdate, Route
from assessor_ai.logging import get_logger

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


async def no_roteador(estado: Estado) -> EstadoUpdate:

    saida = await router_app.ainvoke({"messages": mensagens_com_contexto(estado, incluir_pergunta=False)})
    texto = saida["messages"][-1].content
    rota  = _extrair_rota(texto)
    pergunta = _extrair_pergunta(texto)
    
    log.debug(f"Rota escolhida: {rota} | pergunta: '{pergunta}'")

    if rota is Route.FIM:
        return EstadoUpdate(
            agentes_chamados=[ROTEADOR],
            rota=Route.FIM,
            pergunta_original=pergunta,
            messages=[{"role": "assistant", "content": texto}],
        )

    return EstadoUpdate(
        agentes_chamados=[ROTEADOR],
        rota=rota,
        pergunta_original=pergunta,
    )
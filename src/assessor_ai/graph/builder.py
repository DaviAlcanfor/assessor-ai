import asyncio

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import END, StateGraph

from assessor_ai.graph.agents.nodes import (
    no_agenda,
    no_faq,
    no_financeiro,
    no_guardrail_entrada,
    no_guardrail_saida,
    no_orquestrador,
    no_roteador,
)
from assessor_ai.graph.agents.nodes.names import (
    AGENDA,
    FAQ,
    FINANCEIRO,
    GUARDRAIL_ENTRADA,
    GUARDRAIL_SAIDA,
    ORQUESTRADOR,
    ROTEADOR,
)
from assessor_ai.graph.state import Estado, Route
from assessor_ai.infra.postgres import postgres


def decidir_apos_guardrail_entrada(estado: Estado) -> str:
    if estado.get("mensagem_bloqueada"):
        return Route.FIM
    return ROTEADOR


def decidir_especialista(estado: Estado) -> str:
    rota = estado.get("rota", Route.FIM)
    if rota not in (Route.FINANCEIRO, Route.AGENDA, Route.FAQ):
        return Route.FIM
    return rota


grafo = StateGraph(Estado)

grafo.add_node(GUARDRAIL_ENTRADA, no_guardrail_entrada)
grafo.add_node(ROTEADOR,           no_roteador)
grafo.add_node(FINANCEIRO,         no_financeiro)
grafo.add_node(AGENDA,             no_agenda)
grafo.add_node(FAQ,                no_faq)
grafo.add_node(ORQUESTRADOR,       no_orquestrador)
grafo.add_node(GUARDRAIL_SAIDA,    no_guardrail_saida)


grafo.set_entry_point(GUARDRAIL_ENTRADA)

grafo.add_conditional_edges(
    source   = GUARDRAIL_ENTRADA,
    path     = decidir_apos_guardrail_entrada,
    path_map = {
        Route.FIM:         END,
        ROTEADOR: ROTEADOR,
    },
)

grafo.add_conditional_edges(
    source   = ROTEADOR,
    path     = decidir_especialista,
    path_map = {
        Route.FINANCEIRO: FINANCEIRO,
        Route.AGENDA:     AGENDA,
        Route.FAQ:        FAQ,
        Route.FIM:        END,
    },
)

grafo.add_edge(FINANCEIRO,      ORQUESTRADOR)
grafo.add_edge(AGENDA,          ORQUESTRADOR)
grafo.add_edge(ORQUESTRADOR,    GUARDRAIL_SAIDA)
grafo.add_edge(FAQ,             GUARDRAIL_SAIDA)
grafo.add_edge(GUARDRAIL_SAIDA, END)


_fluxo = None
_lock = asyncio.Lock()


async def fluxo_agentes():
    """
    Adia a conexão com o Postgres e o `setup()` do checkpointer (que cria as tabelas
    `checkpoints`/`checkpoint_blobs`/`checkpoint_writes`/`checkpoint_migrations`) para o primeiro
    uso real, em vez de acontecer no import do pacote. O lock faz o papel do cache que existia
    aqui quando isso era síncrono: sem ele, dois requests concorrentes no primeiro uso abririam
    dois pools e rodariam `setup()` duas vezes.

    `AsyncPostgresSaver` (e não o `PostgresSaver` síncrono) porque os nós são async e chamam
    `ainvoke` — o saver síncrono não implementa `aget_tuple`/`aput` e estoura NotImplementedError.
    Não usar `from_conn_string()`: é context manager e fecha a conexão na saída do `with`, o que
    morre no primeiro uso num app de vida longa.
    """

    global _fluxo

    async with _lock:
        if _fluxo is None:
            checkpointer = AsyncPostgresSaver(await postgres.checkpointer_pool())
            await checkpointer.setup()
            _fluxo = grafo.compile(checkpointer=checkpointer)

    return _fluxo


__all__ = ["fluxo_agentes"]
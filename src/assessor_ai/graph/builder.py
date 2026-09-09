import asyncio

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

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


def _construir_grafo() -> StateGraph:
    grafo = StateGraph(Estado)

    grafo.add_node(GUARDRAIL_ENTRADA, no_guardrail_entrada)
    grafo.add_node(ROTEADOR,           no_roteador)
    grafo.add_node(FINANCEIRO,         no_financeiro)
    grafo.add_node(AGENDA,             no_agenda)
    grafo.add_node(FAQ,               no_faq)
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

    return grafo


class FluxoAgentes:
    """
    Compila o grafo + prepara o checkpointer uma vez por processo e reusa nas requests.

    O `setup()` do `AsyncPostgresSaver` cria as tabelas `checkpoints`/`checkpoint_blobs`/
    `checkpoint_writes`/`checkpoint_migrations` — pagar isso na primeira mensagem faria o primeiro
    usuário do deploy esperar por infra, então o `lifespan` chama `get()` no startup. O lock cobre
    os outros pontos de entrada (TUI, testes) que chamam `get()` sem passar pelo lifespan: sem ele,
    dois `get()` concorrentes no primeiro uso abririam dois pools e rodariam `setup()` duas vezes.

    `AsyncPostgresSaver` (e não o `PostgresSaver` síncrono) porque os nós são async e chamam
    `ainvoke` — o saver síncrono não implementa `aget_tuple`/`aput` e estoura NotImplementedError.
    Não usar `from_conn_string()`: é context manager e fecha a conexão na saída do `with`, o que
    morre no primeiro uso num app de vida longa.
    """

    def __init__(self) -> None:
        self._compilado: CompiledStateGraph[Estado] | None = None
        self._lock = asyncio.Lock()


    async def get(self) -> CompiledStateGraph[Estado]:
        if self._compilado is not None:
            return self._compilado

        async with self._lock:
            if self._compilado is None:
                checkpointer = AsyncPostgresSaver(await postgres.checkpointer_pool())
                await checkpointer.setup()
                self._compilado = _construir_grafo().compile(checkpointer=checkpointer)

        return self._compilado


    async def aclose(self) -> None:
        """
        Invalida o grafo compilado. Chamado pelo lifespan no shutdown, antes de `postgres.dispose()`
        fechar o pool: sem isso, um segundo ciclo de lifespan no mesmo processo (suíte com
        `TestClient`, reload) devolveria um grafo amarrado a um pool já fechado.
        """

        async with self._lock:
            self._compilado = None


fluxo_agentes = FluxoAgentes()


__all__ = ["FluxoAgentes", "fluxo_agentes"]

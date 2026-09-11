import logging
import time
from collections.abc import AsyncIterator, Sequence
from typing import cast, get_args

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage
from langchain_core.runnables import RunnableConfig

from assessor_ai.graph.agents.nodes.names import GUARDRAIL_SAIDA, ROTEADOR, NodeName
from assessor_ai.graph.builder import fluxo_agentes
from assessor_ai.graph.state import Estado, Route, SaidaGrafo
from assessor_ai.identifiers import (
    ChatID,
    UserID,
    reset_usuario_atual,
    set_usuario_atual,
)
from assessor_ai.infra.postgres import reset_current_user, set_current_user
from assessor_ai.logging import get_logger
from assessor_ai.metrics import GRAPH_DURATION, GRAPH_RUNS
from assessor_ai.metrics_callbacks import PrometheusCallbackHandler
from assessor_ai.schemas.execution import (
    AnswerReady,
    ExecutionEvent,
    NodeFinished,
    NodeStarted,
    RouteSelected,
    RunFailed,
    RunFinished,
    RunStarted,
)
from assessor_ai.schemas.models import ChatMessage, Role

logger = get_logger(__name__)

# O aviso "Deserializing unregistered type" sai por `logger.warning` do serde do langgraph, não
# pelo módulo `warnings` — filtrar em `warnings.filterwarnings` era no-op. Silenciado no logger do
# módulo que emite, e não no logger `langgraph` inteiro, pra não engolir o resto.
# ponytail: o fix de raiz é passar `allowed_msgpack_modules` no serde do checkpointer, mas a lista
# liga o modo estrito (bloqueia o que não estiver nela) — trocar só com teste ponta a ponta.
logging.getLogger("langgraph.checkpoint.serde.jsonplus").setLevel(logging.ERROR)


_PARA_LANGCHAIN = {
    Role.HUMAN: HumanMessage,
    Role.AI: AIMessage,
}


def _ultima_resposta_ia(mensagens: Sequence[AnyMessage]) -> str | None:
    for msg in mensagens[::-1]:
        if isinstance(msg, AIMessage):
            return msg.text
    return None


def _extrair_resposta(estado_final: SaidaGrafo) -> str | None:
    return _ultima_resposta_ia(estado_final["messages"])


# Nomes registrados via StateGraph.add_node() — event["name"] do astream_events bate com essa
# string exata pro evento de início/fim do node em si (metadata["langgraph_node"] é herdado por
# todo runnable filho, event["name"] não é: por isso filtramos por name, não por metadata).
# get_args(NodeName) sozinho devolve () — NodeName é um `type` alias (PEP 695), get_args só
# enxerga o Literal por trás dele via `.__value__`.
_NOMES_DE_NODE = frozenset(get_args(NodeName.__value__))


async def executar(
    mensagem: ChatMessage, session_id: ChatID, perfil_usuario: str, user_id: UserID
) -> str | None:
    estado_inicial: Estado = {
        "messages": [_PARA_LANGCHAIN[mensagem.role](content=mensagem.content)],
        "agentes_chamados": [],
        "perfil_usuario": perfil_usuario,
    }

    config: RunnableConfig = {
        "configurable": {"thread_id": session_id},
        "tags": ["chat"],
        "metadata": {"user_id": user_id, "session_id": session_id},
        "callbacks": [PrometheusCallbackHandler()],
    }

    # As tools síncronas de Postgres/Mongo/Qdrant rodam em thread do executor do LangChain, que
    # copia o contextvar da task atual — por isso os `set_*` aqui continuam valendo lá dentro.
    token = set_current_user(user_id)
    token_usuario = set_usuario_atual(user_id)
    inicio = time.perf_counter()
    outcome = "error"
    try:
        grafo = await fluxo_agentes.get()
        # ainvoke() devolve tipo fraco no stub do langgraph mesmo com output_schema declarado.
        estado_final = cast(SaidaGrafo, await grafo.ainvoke(estado_inicial, config=config))
        outcome = "success"
    finally:
        reset_current_user(token)
        reset_usuario_atual(token_usuario)
        duracao = time.perf_counter() - inicio
        GRAPH_RUNS.labels(outcome=outcome).inc()
        GRAPH_DURATION.labels(outcome=outcome).observe(duracao)

    return _extrair_resposta(estado_final)


async def executar_stream(
    mensagem: ChatMessage, session_id: ChatID, perfil_usuario: str, user_id: UserID
) -> AsyncIterator[ExecutionEvent]:
    """
    Mesma execução de `executar()`, mas emite a timeline de nodes em tempo real via
    `astream_events`. Não faz streaming de token da resposta final — ver `schemas/execution.py`
    (`AnswerReady`) pra explicação.
    """

    estado_inicial: Estado = {
        "messages": [_PARA_LANGCHAIN[mensagem.role](content=mensagem.content)],
        "agentes_chamados": [],
        "perfil_usuario": perfil_usuario,
    }

    config: RunnableConfig = {
        "configurable": {"thread_id": session_id},
        "tags": ["chat"],
        "metadata": {"user_id": user_id, "session_id": session_id},
        "callbacks": [PrometheusCallbackHandler()],
    }

    yield RunStarted()

    token = set_current_user(user_id)
    token_usuario = set_usuario_atual(user_id)
    inicio = time.perf_counter()
    outcome = "error"

    try:
        grafo = await fluxo_agentes.get()
        resposta_final: str | None = None

        async for event in grafo.astream_events(estado_inicial, config=config, version="v2"):
            nome = event.get("name")

            if nome not in _NOMES_DE_NODE:
                continue

            tipo = event.get("event")

            if tipo == "on_chain_start":
                yield NodeStarted(node=cast(NodeName, nome))
                continue

            if tipo != "on_chain_end":
                continue

            output = event.get("data", {}).get("output")

            if isinstance(output, dict):
                if nome == ROTEADOR:
                    rota = output.get("rota")

                    if isinstance(rota, Route):
                        yield RouteSelected(route=rota)

                    if rota is Route.FIM:
                        resposta_final = _ultima_resposta_ia(output.get("messages", []))

                if nome == GUARDRAIL_SAIDA:
                    resposta_final = _ultima_resposta_ia(output.get("messages", []))

            yield NodeFinished(node=cast(NodeName, nome))

        outcome = "success"

        if resposta_final is not None:
            yield AnswerReady(content=resposta_final)

        yield RunFinished()
    except Exception:
        logger.exception("Falha durante streaming da execução do agente")
        yield RunFailed(message="Não foi possível processar a mensagem.")
    finally:
        reset_current_user(token)
        reset_usuario_atual(token_usuario)
        duracao = time.perf_counter() - inicio
        GRAPH_RUNS.labels(outcome=outcome).inc()
        GRAPH_DURATION.labels(outcome=outcome).observe(duracao)


__all__ = ["executar", "executar_stream"]

from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import (
    add_a2a_routes_to_fastapi,
    create_agent_card_routes,
    create_jsonrpc_routes,
)
from a2a.server.tasks import InMemoryTaskStore
from fastapi import FastAPI

from assessor_ai.a2a.agents.card import AGENT_CARD
from assessor_ai.a2a.agents.interface import AssessorAgentExecutor

RPC_URL = "/a2a"


def montar_rotas(app: FastAPI) -> None:
    """Registra as rotas do protocolo A2A (agent card + JSON-RPC) no app FastAPI existente."""

    handler = DefaultRequestHandler(
        agent_executor=AssessorAgentExecutor(),
        task_store=InMemoryTaskStore(),
        agent_card=AGENT_CARD,
    )

    add_a2a_routes_to_fastapi(
        app,
        agent_card_routes=create_agent_card_routes(AGENT_CARD),
        jsonrpc_routes=create_jsonrpc_routes(handler, rpc_url=RPC_URL),
    )

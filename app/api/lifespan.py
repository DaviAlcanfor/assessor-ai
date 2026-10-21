"""
Recursos que a API monta uma vez por processo. É o único lugar da camada `api/` que abre e fecha
infra — o que já tem ciclo de vida próprio (pool do Postgres em `tools/postgres/connection.py`,
cliente do Mongo, do Redis e do Qdrant) continua lazy e não é duplicado aqui.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.mcp import lifespan_mcp
from app.graph.builder import fluxo_agentes
from app.infra.logging import Logging
from app.infra.postgres import postgres

logger = Logging.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    # Compila o grafo e roda o `setup()` do checkpointer aqui, e não na primeira mensagem: o
    # `setup()` cria tabelas no Postgres, e pagar isso dentro de um request faz o primeiro
    # usuário do deploy esperar por infra. Falhar aqui também é melhor — o processo não sobe
    # com o Postgres fora do ar em vez de aceitar tráfego e errar 502 em cada mensagem.
    await fluxo_agentes.get()
    logger.info("Grafo de agentes compilado e checkpointer pronto.")

    async with lifespan_mcp(app):
        yield

    await fluxo_agentes.aclose()
    await postgres.dispose()


__all__ = ["lifespan"]

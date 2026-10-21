from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.mcp.server import mcp_starlette


@asynccontextmanager
async def lifespan_mcp(app: FastAPI) -> AsyncGenerator[None]:
    """O sub-app do MCP (montado em /mcp) tem o próprio lifespan (`session_manager.run()`), que o
    Starlette não dispara sozinho num Mount — o lifespan da API precisa entrar neste context."""

    async with mcp_starlette.router.lifespan_context(app):
        yield


__all__ = ["lifespan_mcp"]

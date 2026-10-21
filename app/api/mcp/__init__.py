"""Servidor MCP do Assessor.AI: mais uma porta de entrada sobre os mesmos services/tools, pra clientes
como Claude Desktop e IDEs. Montado em `/mcp` e autenticado por `X-API-Key`."""

from fastapi import FastAPI

from app.api.mcp.auth import IdentidadeMCP
from app.api.mcp.lifespan import lifespan_mcp
from app.api.mcp.server import mcp_starlette


def montar_mcp(app: FastAPI) -> None:
    app.mount("/mcp", IdentidadeMCP(mcp_starlette), name="mcp")


__all__ = ["lifespan_mcp", "montar_mcp"]

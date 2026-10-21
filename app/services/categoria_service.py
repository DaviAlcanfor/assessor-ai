"""Casos de uso das categorias financeiras (rota HTTP e resource do MCP)."""

import asyncio

from app.repositories import categoria_repository
from app.repositories.categoria_repository import CategoriaRecord


async def listar() -> list[CategoriaRecord]:
    return await asyncio.to_thread(categoria_repository.listar)


__all__ = ["listar"]

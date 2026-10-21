from mcp.server.mcpserver import MCPServer

from app.services import categoria_service


def registrar_resources(servidor: MCPServer) -> None:
    @servidor.resource("categories://all", name="categorias", mime_type="application/json")
    async def listar_categorias() -> list[dict[str, object]]:
        """Categorias disponíveis pra usar em `category_name` ao registrar uma transação."""

        return [dict(c) for c in await categoria_service.listar()]


__all__ = ["registrar_resources"]

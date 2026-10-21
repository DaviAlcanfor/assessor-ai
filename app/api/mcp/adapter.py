"""
Expõe as tools do LangChain (as mesmas que os agentes usam) como tools MCP, sem reescrever assinatura
nenhuma à mão.

O `MCPServer` monta o schema da tool a partir da assinatura da função. Aqui a assinatura é montada a
partir do `args_schema` Pydantic da tool, campo a campo — assim `description`, `ge`/`le` e os tipos
chegam ao cliente MCP exatamente como chegam ao LLM do Assessor.AI, e uma tool nova aparece no MCP sozinha.
"""

import inspect
from collections.abc import Awaitable, Callable, Iterable
from typing import Annotated, Any

from langchain_core.tools import BaseTool
from mcp.server.mcpserver import MCPServer
from pydantic import BaseModel, Field

from app.api.mcp.annotations import anotacao_da_tool


def _assinatura(args_schema: type[BaseModel]) -> inspect.Signature:
    parametros = []

    for nome, campo in args_schema.model_fields.items():
        # O tipo só existe em runtime (vem do campo), por isso `Any` pro mypy.
        anotacao: Any = Annotated[(campo.annotation, Field(description=campo.description), *campo.metadata)]
        parametros.append(
            inspect.Parameter(
                nome,
                inspect.Parameter.KEYWORD_ONLY,
                default=inspect.Parameter.empty if campo.is_required() else campo.default,
                annotation=anotacao,
            )
        )

    return inspect.Signature(parametros)


def _adaptar(tool: BaseTool) -> Callable[..., Awaitable[Any]]:
    async def executar(**argumentos: Any) -> Any:
        # `ainvoke` roda a tool síncrona numa thread que herda o contexto — o `session_context()`
        # aberto pelo middleware (`api/mcp/auth.py`) continua valendo lá dentro.
        return await tool.ainvoke(argumentos)

    executar.__name__ = tool.name
    executar.__doc__ = tool.description
    if tool.args_schema is not None and inspect.isclass(tool.args_schema) and issubclass(tool.args_schema, BaseModel):
        executar.__signature__ = _assinatura(tool.args_schema)  # type: ignore[attr-defined]

    return executar


def _titulo(nome: str) -> str:
    return nome.replace("_", " ").capitalize()


def registrar_tools(servidor: MCPServer, tools: Iterable[BaseTool]) -> None:
    for tool in tools:
        servidor.add_tool(
            _adaptar(tool),
            name=tool.name,
            title=_titulo(tool.name),
            description=tool.description,
            annotations=anotacao_da_tool(tool.name),
        )


__all__ = ["registrar_tools"]

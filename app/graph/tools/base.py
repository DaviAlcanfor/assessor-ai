import inspect
from collections.abc import Mapping
from typing import Any, ClassVar

from langchain_core.tools import StructuredTool
from pydantic import BaseModel

from app.graph.tools.response import Response
from app.infra.logging import Logging

_IGNORADOS = frozenset({"as_tools"})

# nome da tool → `args_schema` Pydantic
type Schemas = Mapping[str, type[BaseModel]]


class ToolSet:
    """
    Contrato de todo domínio de tools do grafo. Cada método público é uma tool; `as_tools()` as entrega
    ao LangChain.

    `schemas` mapeia o nome da tool ao `args_schema` Pydantic (o que o LLM vê: tipos, descrições e
    limites). Tool sem entrada usa a assinatura do método. A docstring do método vira a descrição.

    `as_tools` é método de instância e usa `StructuredTool.from_function` num bound method: `@tool`
    nos métodos rodaria no corpo da classe, quando `self` ainda está na assinatura, e vazaria pro JSON
    schema que vai pro LLM.

    Todo método público de toda subclasse já sai com `Response.catch` (exceção vira `Response.error`) e
    logado (`Logging.log_classe`, com PII redigida): não precisa de `try/except` nem de log por método.
    Helper que não é tool começa com `_`.
    """

    schemas: ClassVar[Schemas] = {}

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)

        for nome, atributo in list(vars(cls).items()):
            if nome.startswith("_") or nome in _IGNORADOS or not inspect.isfunction(atributo):
                continue
            setattr(cls, nome, Response.catch(atributo))

        Logging.log_classe(ignore=_IGNORADOS)(cls)

    def as_tools(self) -> list[StructuredTool]:
        tools: list[StructuredTool] = []

        for nome, atributo in vars(type(self)).items():
            if nome.startswith("_") or nome in _IGNORADOS or not inspect.isfunction(atributo):
                continue

            metodo = getattr(self, nome)
            execucao: dict[str, Any] = (
                {"coroutine": metodo} if inspect.iscoroutinefunction(atributo) else {"func": metodo}
            )
            tools.append(
                StructuredTool.from_function(
                    name=nome, args_schema=self.schemas.get(nome), **execucao
                )
            )

        return tools


__all__ = ["Schemas", "ToolSet"]

import functools
import inspect
from collections.abc import Callable
from enum import StrEnum
from typing import Any, Literal, TypedDict

from app.domain.errors import DomainError
from app.infra.logging import Logging

logger = Logging.get_logger(__name__)

_ERRO_GENERICO = "Erro interno ao executar a ferramenta."


class ResponseStatus(StrEnum):
    OK = "ok"
    ERROR = "error"


# Sucesso: `status` garantido + um payload livre que varia por tool (results, cadastrado, id,
# events, rows_affected...). Não dá pra fechar num TypedDict sem enumerar tool por tool.
type ToolResponseOk = dict[str, object]


class ToolResponseError(TypedDict):
    status: Literal[ResponseStatus.ERROR]
    message: str


type ToolResponse = ToolResponseOk | ToolResponseError


class Response:
    @staticmethod
    def ok(**kwargs: object) -> ToolResponseOk:
        return {"status": ResponseStatus.OK, **kwargs}

    @staticmethod
    def error(message: Exception | str) -> ToolResponseError:
        return {"status": ResponseStatus.ERROR, "message": str(message)}

    @staticmethod
    def _de_excecao(e: Exception) -> ToolResponseError:
        """`DomainError` carrega mensagem escrita pra quem chamou (aqui, o LLM). Qualquer outra exceção
        pode trazer query, connection string ou payload: vai pro log com o traceback e o LLM recebe um
        texto genérico."""

        if isinstance(e, DomainError):
            return Response.error(e.public_message)

        logger.exception("Falha inesperada numa tool")
        return Response.error(_ERRO_GENERICO)

    @staticmethod
    def catch(func: Callable[..., Any]) -> Callable[..., Any]:
        """Converte qualquer exception que a tool levantar em `Response.error` — tira o `try/except`
        repetido de cada método. O log de CHAMANDO/OK/ERRO fica com `Logging.log_classe` (ver
        `ToolSet`), então o método em si não precisa logar nada.

        Preserva sync/async: o `log_tool` aplicado por cima decide qual wrapper usar com
        `inspect.iscoroutinefunction` — se aqui sempre devolvesse uma função sync (mesmo embrulhando
        um método `async def`), ele acharia que é síncrono, chamaria sem `await` e logaria "OK" com a
        coroutine ainda por rodar."""

        if inspect.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> ToolResponse:
                try:
                    return await func(*args, **kwargs)  # type: ignore[no-any-return]
                except Exception as e:
                    return Response._de_excecao(e)

            return async_wrapper

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> ToolResponse:
            try:
                return func(*args, **kwargs)  # type: ignore[no-any-return]
            except Exception as e:
                return Response._de_excecao(e)

        return wrapper


__all__ = [
    "Response",
    "ResponseStatus",
    "ToolResponse",
    "ToolResponseError",
    "ToolResponseOk",
]

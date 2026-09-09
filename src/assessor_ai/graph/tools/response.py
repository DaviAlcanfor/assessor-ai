from enum import StrEnum
from typing import Literal, TypedDict


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


__all__ = [
    "Response",
    "ResponseStatus",
    "ToolResponse",
    "ToolResponseError",
    "ToolResponseOk",
]

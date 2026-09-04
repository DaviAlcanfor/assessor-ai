from enum import StrEnum


class ResponseStatus(StrEnum):
    OK = "ok"
    ERROR = "error"


type ToolResponse = dict[str, object]


class Response:
    @staticmethod
    def ok(**kwargs: object) -> ToolResponse:
        return {
            "status": ResponseStatus.OK,
            **kwargs
        }

    @staticmethod
    def error(message: Exception | str) -> ToolResponse:
        return {
            "status": ResponseStatus.ERROR,
            "message": str(message)
        }
        
__all__ = ["Response", "ResponseStatus", "ToolResponse"]
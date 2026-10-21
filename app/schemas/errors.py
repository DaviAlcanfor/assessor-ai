from pydantic import BaseModel

from app.domain.errors import ErrorCode


class ErrorResponse(BaseModel):
    detail: str
    code: ErrorCode


__all__ = ["ErrorCode", "ErrorResponse"]

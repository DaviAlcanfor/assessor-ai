from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel

from assessor_ai.identifiers import UserID


class AuthMethod(StrEnum):
    API_KEY = "api_key"
    SESSION = "session"
    DEV = "dev"


@dataclass(frozen=True, slots=True)
class Principal:
    user_id: UserID
    auth_method: AuthMethod
    csrf_hash: str | None = None


class SessionCreateResponse(BaseModel):
    user_id: UserID
    expires_at: datetime


class CurrentPrincipalResponse(BaseModel):
    user_id: UserID
    auth_method: AuthMethod


__all__ = [
    "AuthMethod",
    "CurrentPrincipalResponse",
    "Principal",
    "SessionCreateResponse",
]

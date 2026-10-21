from enum import StrEnum

from pydantic import BaseModel


class Role(StrEnum):
    HUMAN = "human"
    AI    = "ai"


class ChatMessage(BaseModel):
    role:    Role
    content: str


__all__ = ["ChatMessage", "Role"]

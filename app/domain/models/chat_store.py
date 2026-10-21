"""Como o chat é guardado (Mongo): o documento, o registro lido de volta e a mensagem persistida.

`ChatMessage`/`Role` (em `chat.py`) são o contrato de quem conversa; estes são o formato de gravação.
"""

from datetime import UTC, datetime
from enum import StrEnum
from typing import TypedDict

from pydantic import BaseModel, Field

from app.domain.types import ChatID, UserID


class Role(StrEnum):
    HUMAN = "human"
    AI    = "ai"


class MessageDocument(TypedDict):
    role: Role
    content: str


class ChatDocument(BaseModel):
    user_id:    UserID
    session_id: ChatID
    messages:   list[MessageDocument]
    resume:     str      = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ChatRecord(TypedDict, total=False):
    user_id: UserID
    session_id: ChatID
    messages: list[MessageDocument]
    resume: str
    created_at: datetime
    updated_at: datetime


class Mensagem(BaseModel):
    role:    Role
    content: str

    @staticmethod
    def de_dict(msgs: list[MessageDocument]) -> list["Mensagem"]:
        return [Mensagem(role=m["role"], content=m["content"]) for m in msgs]

    def para_dict(self) -> MessageDocument:
        return {"role": self.role, "content": self.content}


__all__ = ["ChatDocument", "ChatRecord", "Mensagem", "MessageDocument", "Role"]

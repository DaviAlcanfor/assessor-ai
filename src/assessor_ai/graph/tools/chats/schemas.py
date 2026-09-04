from datetime import UTC, datetime
from enum import StrEnum
from typing import TypedDict

from langchain_core.messages import AIMessage, HumanMessage
from pydantic import BaseModel, Field

from assessor_ai.identifiers import ChatID, UserID


class ChatDocument(BaseModel):
    user_id:    UserID
    session_id: ChatID
    messages:   list["MessageDocument"]
    resume:     str      = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Role(StrEnum):
    HUMAN = "human"
    AI    = "ai"


ROLE_MAP = {
    Role.HUMAN: HumanMessage,
    Role.AI:    AIMessage,
}


class MessageDocument(TypedDict):
    role: Role
    content: str


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
    def de_langchain(msgs: list[AIMessage | HumanMessage]) -> list["Mensagem"]:
        return [
            Mensagem(role=m.type, content=m.content)
            for m in msgs
            if m.type in ROLE_MAP
        ]

    def para_langchain(self) -> HumanMessage | AIMessage:
        return ROLE_MAP[self.role](content=self.content)

    @staticmethod
    def de_dict(msgs: list[MessageDocument]) -> list["Mensagem"]:
        return [
            Mensagem(role=m["role"], content=m["content"]) 
            for m in msgs
        ]

    def para_dict(self) -> MessageDocument:
        return {
            "role": self.role, 
            "content": self.content
        }


__all__ = ["ChatDocument", "ChatRecord", "Mensagem", "MessageDocument", "Role"]

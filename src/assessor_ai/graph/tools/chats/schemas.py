from datetime import UTC, datetime
from enum import StrEnum

from langchain_core.messages import AIMessage, HumanMessage
from pydantic import BaseModel, Field


class ChatDocument(BaseModel):
    user_id:    str
    session_id: str
    messages:   list[dict]
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


class Mensagem(BaseModel):
    role:    Role
    content: str

    @staticmethod
    def de_langchain(msgs: list) -> list["Mensagem"]:
        return [
            Mensagem(role=m.type, content=m.content)
            for m in msgs
            if m.type in ROLE_MAP
        ]

    def para_langchain(self):
        return ROLE_MAP[self.role](content=self.content)

    @staticmethod
    def de_dict(msgs: list[dict]) -> list["Mensagem"]:
        return [Mensagem(role=m["role"], content=m["content"]) for m in msgs]

    def para_dict(self) -> dict:
        return {"role": self.role, "content": self.content}

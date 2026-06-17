from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum

from langchain_core.messages import HumanMessage, AIMessage



@dataclass
class ChatDocument:
    user_id:    str
    session_id: str
    messages:   list[dict]
    resume:     str      = field(default="")
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))



class Role(StrEnum):
    HUMAN = "human"
    AI    = "ai"
    
    
ROLE_MAP = {
    Role.HUMAN: HumanMessage,
    Role.AI:    AIMessage,
}


@dataclass
class Mensagem:
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

from dataclasses import dataclass, field
from datetime import datetime, timezone

from langchain_core.messages import HumanMessage, AIMessage


ROLE_MAP = {
    "human": HumanMessage,
    "ai":    AIMessage,
}

@dataclass
class Mensagem:
    role:    str
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


@dataclass
class UserDocument:
    nome:    str
    email:   str
    profile: str = field(default="")


@dataclass
class ChatDocument:
    user_id:    str
    session_id: str
    messages:   list[dict]
    resume:     str      = field(default="")
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
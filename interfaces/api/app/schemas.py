from pydantic import BaseModel, Field
from enum import StrEnum


class Role(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"


class Message(BaseModel):
    role: Role = Field(..., description="The role of the message sender.")
    content: str = Field(..., description="The content of the message.")
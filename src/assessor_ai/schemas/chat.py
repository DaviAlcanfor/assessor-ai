from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class Role(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"


class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=4000)


class MessageResponse(BaseModel):
    role: Role
    content: str


class ChatCreateResponse(BaseModel):
    chat_id: str


class ChatMessageResponse(BaseModel):
    chat_id: str
    content: str


class ChatSummary(BaseModel):
    chat_id: str
    title: str
    updated_at: datetime
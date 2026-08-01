from pydantic import BaseModel, Field
from datetime import datetime
from enum import StrEnum


class Role(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"


class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=4000)


class MessageResponse(BaseModel):
    role: Role
    content: str
    created_at: datetime


class ChatCreateResponse(BaseModel):
    chat_id: str


class ChatMessageResponse(BaseModel):
    chat_id: str
    content: str
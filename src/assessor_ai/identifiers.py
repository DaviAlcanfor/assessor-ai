from typing import NewType
from uuid import uuid4

UserID = NewType("UserID", str)
ChatID = NewType("ChatID", str)
APIKey = NewType("APIKey", str)
APIKeyHash = NewType("APIKeyHash", str)


def novo_chat_id() -> ChatID:
    return ChatID(str(uuid4()))


def novo_user_id() -> UserID:
    return UserID(str(uuid4()))


__all__ = [
    "APIKey",
    "APIKeyHash",
    "ChatID",
    "UserID",
    "novo_chat_id",
    "novo_user_id",
]

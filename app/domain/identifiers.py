from uuid import uuid4

from app.domain.types import ChatID, UserID


def novo_chat_id() -> ChatID:
    return ChatID(str(uuid4()))


def novo_user_id() -> UserID:
    return UserID(str(uuid4()))


__all__ = ["novo_chat_id", "novo_user_id"]

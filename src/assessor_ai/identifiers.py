from contextvars import ContextVar, Token
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


# default="" (fora de request): filtro por "" não casa com ninguém → a tool degrada pra "sem
# cadastro". noqa porque o ruff lê `UserID(...)` como estrutura mutável — falso-positivo em NewType.
_usuario_atual: ContextVar[UserID] = ContextVar("usuario_atual", default=UserID(""))  # noqa: B039


def set_usuario_atual(user_id: UserID) -> Token[UserID]:
    return _usuario_atual.set(user_id)


def reset_usuario_atual(token: Token[UserID]) -> None:
    _usuario_atual.reset(token)


def usuario_atual() -> UserID:
    return _usuario_atual.get()


__all__ = [
    "APIKey",
    "APIKeyHash",
    "ChatID",
    "UserID",
    "novo_chat_id",
    "novo_user_id",
    "reset_usuario_atual",
    "set_usuario_atual",
    "usuario_atual",
]

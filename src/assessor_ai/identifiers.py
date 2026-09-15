from contextvars import ContextVar, Token
from typing import Annotated, NewType
from uuid import uuid4

from pydantic import Field

UserIDField = NewType("UserIDField", str)
ChatIDField = NewType("ChatIDField", str)
APIKeyField = NewType("APIKeyField", str)
APIKeyHash = NewType("APIKeyHash", str)
SessionToken = NewType("SessionToken", str)
CsrfToken = NewType("CsrfToken", str)

UserID = Annotated[
    UserIDField,
    Field(
        description="Identificador único do usuário.", 
        examples=["b194361d-2434-4d1e-95a7-480c6cf89c9e"]
    ),
]
ChatID = Annotated[
    ChatIDField,
    Field(
        description="Identificador único do chat.", 
        examples=["9979d729-681c-46ec-8741-b37fae55d9d7"]
    ),
]
APIKey = Annotated[
    APIKeyField,
    Field(
        description="Chave de API do usuário, usada no header X-API-Key.", 
        examples=["sk_live_51H8x..."]
    ),
]


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
    # ponytail: swallow ValueError — quando o consumidor do SSE cai no meio do stream (conexão
    # derrubada), o async generator de executar_stream vira órfão e o event loop o fecha via
    # GeneratorExit num Context novo (asyncgen finalizer), diferente daquele onde o token foi
    # criado. `.reset()` nesse Context sempre falha; não tem "certo" a fazer além de ignorar — o
    # ContextVar órfão some junto com o Context quando ele for coletado.
    try:
        _usuario_atual.reset(token)
    except ValueError:
        pass


def usuario_atual() -> UserID:
    return _usuario_atual.get()


__all__ = [
    "APIKey",
    "APIKeyField",
    "APIKeyHash",
    "ChatID",
    "ChatIDField",
    "CsrfToken",
    "SessionToken",
    "UserID",
    "UserIDField",
    "novo_chat_id",
    "novo_user_id",
    "reset_usuario_atual",
    "set_usuario_atual",
    "usuario_atual",
]

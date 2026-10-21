"""
Tipos de identificação compartilhados entre camadas.

Cada ID é um `NewType` (o mypy estrito pega troca de argumento, ex.: `ChatID` onde se esperava `UserID`)
embrulhado num `Annotated[..., Field(...)]`, que só tem efeito onde vira schema Pydantic — descrição e
exemplo aparecem no OpenAPI. Fora disso é só o `NewType`.
"""

from typing import Annotated, NewType

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
        examples=["b194361d-2434-4d1e-95a7-480c6cf89c9e"],
    ),
]
ChatID = Annotated[
    ChatIDField,
    Field(
        description="Identificador único do chat.",
        examples=["9979d729-681c-46ec-8741-b37fae55d9d7"],
    ),
]
APIKey = Annotated[
    APIKeyField,
    Field(
        description="Chave de API do usuário, usada no header X-API-Key.",
        examples=["sk_live_51H8x..."],
    ),
]


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
]

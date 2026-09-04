import hashlib
from typing import TypedDict

from pydantic import BaseModel, EmailStr

from assessor_ai.identifiers import APIKey, APIKeyHash, UserID


class UserDocument(BaseModel):
    user_id: UserID
    nome:    str
    email:   EmailStr
    profile: str = ""


class UserRecord(TypedDict, total=False):
    user_id: UserID
    nome: str
    email: str
    profile: str


API_KEY_TTL_TIME = 3600 * 24


def hash_api_key(api_key: APIKey) -> APIKeyHash:
    return APIKeyHash(hashlib.sha256(api_key.encode()).hexdigest())


def chave_api_key(user_id: UserID) -> str:
    return f"auth:user:{user_id}:api-key-hash"


def chave_api_key_lookup(hashed_key: APIKeyHash) -> str:
    return f"auth:api-key:{hashed_key}"


__all__ = [
    "API_KEY_TTL_TIME",
    "UserDocument",
    "UserRecord",
    "chave_api_key",
    "chave_api_key_lookup",
    "hash_api_key",
]

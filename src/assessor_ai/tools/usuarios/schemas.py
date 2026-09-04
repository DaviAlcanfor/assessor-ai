import hashlib

from pydantic import BaseModel, EmailStr


class UserDocument(BaseModel):
    user_id: str
    nome:    str
    email:   EmailStr
    profile: str = ""


API_KEY_TTL_TIME = 3600 * 24


def hash_api_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode()).hexdigest()


def chave_api_key(user_id: str) -> str:
    return f"auth:user:{user_id}:api-key-hash"


def chave_api_key_lookup(hashed_key: str) -> str:
    return f"auth:api-key:{hashed_key}"


__all__ = [
    "API_KEY_TTL_TIME",
    "UserDocument",
    "chave_api_key",
    "chave_api_key_lookup",
    "hash_api_key",
]

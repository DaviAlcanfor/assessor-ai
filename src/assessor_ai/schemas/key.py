from pydantic import BaseModel, EmailStr, Field

from assessor_ai.identifiers import APIKeyField, UserIDField


class KeyCreate(BaseModel):
    nome: str = Field(..., min_length=1, max_length=200)
    email: EmailStr = Field(..., min_length=3, max_length=320)


class KeyCreateResponse(BaseModel):
    user_id: UserIDField
    api_key: APIKeyField

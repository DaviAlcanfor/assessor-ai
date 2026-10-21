from pydantic import BaseModel, EmailStr, Field

from app.domain.types import UserIDField


class UserCreate(BaseModel):
    nome: str = Field(min_length=1, max_length=100)
    email: EmailStr


class UserResponse(BaseModel):
    user_id: UserIDField
    nome: str
    email: str

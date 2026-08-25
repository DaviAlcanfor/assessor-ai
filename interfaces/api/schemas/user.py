from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    nome: str = Field(min_length=1, max_length=100)
    email: EmailStr


class UserResponse(BaseModel):
    user_id: str
    nome: str
    email: str

from typing import TypedDict

from pydantic import BaseModel, EmailStr

from app.domain.types import UserID


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


__all__ = ["UserDocument", "UserRecord"]

from pydantic import BaseModel, EmailStr


class UserDocument(BaseModel):
    user_id: str
    nome:    str
    email:   EmailStr
    profile: str = ""

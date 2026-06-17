from dataclasses import dataclass, field



@dataclass
class UserDocument:
    user_id: str
    nome:    str
    email:   str
    profile: str = field(default="")



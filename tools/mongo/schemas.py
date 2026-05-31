from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ChatDocument:
    session_id: str
    messages:   list[dict]
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
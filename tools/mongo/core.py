from dataclasses import asdict
from datetime import datetime

from tools.mongo.connection import banco
from tools.mongo.schemas import ChatDocument

collection = banco["chats"]


def inserir(session_id: str, messages: list[dict]):
    
    document = ChatDocument(
        session_id=session_id,
        messages=messages
    )
    collection.insert_one(asdict(document))

    
def buscar(session_id: str, limit: int = 20) -> dict | None:
    
    return collection.find_one(
        {"session_id": session_id},
        {"messages": {"$slice": -limit}}
    )


def atualizar(session_id: str, messages: list[dict]):
    
    collection.update_one(
    {"session_id": session_id},  
    {"$set": {"messages": messages, 
              "updated_at": datetime.utcnow()}}  
)
from dataclasses import asdict
from datetime import datetime

from tools.mongo.connection import banco
from tools.mongo.schemas import ChatDocument
from config.logging import get_logger

logger = get_logger(__name__)

collection = banco["chats"]


def inserir(session_id: str, messages: list[dict]):
    logger.info(f"Inserindo novo histórico de mensagens para session_id: {session_id}")
    
    document = ChatDocument(
        session_id=session_id,
        messages=messages
    )
    collection.insert_one(asdict(document))

    
def buscar(session_id: str, limit: int = 5) -> dict | None:
    logger.info(f"Buscando histórico de mensagens para session_id: {session_id} (limit={limit})")
    return collection.find_one(
        {"session_id": session_id},
        {"messages": {"$slice": -limit}}
    )


def atualizar(session_id: str, messages: list[dict]):
    
    logger.info(f"Atualizando histórico de mensagens para session_id: {session_id}")
    collection.update_one(
    {"session_id": session_id},  
    {"$set": {"messages": messages, 
              "updated_at": datetime.utcnow()}}  
)
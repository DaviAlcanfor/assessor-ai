from dataclasses import asdict
from datetime import datetime, timezone

from tools.mongo.resumidor import _gerar_resumo
from tools.mongo.connection import banco
from tools.mongo.schemas import ChatDocument, Mensagem
from config.logging import get_logger

logger = get_logger(__name__)

collection = banco["chats"]


def inserir(user_id: str, session_id: str, mensagens: list[Mensagem]) -> None:
    logger.info(f"Inserindo novo histórico de mensagens para session_id: {session_id}")

    document = ChatDocument(
        user_id=user_id,
        session_id=session_id,
        messages=[m.para_dict() for m in mensagens],
    )
    collection.insert_one(asdict(document))


def buscar(session_id: str, limit: int = 5) -> dict | None:
    logger.info(f"Buscando histórico de mensagens para session_id: {session_id} (limit={limit})")

    return collection.find_one(
        {"session_id": session_id},
        {"messages": {"$slice": -limit}}
    )


def adicionar_mensagens(session_id: str, mensagens_novas: list[Mensagem]) -> None:
    logger.info(f"Adicionando mensagens para session_id: {session_id}")

    collection.update_one(
        {"session_id": session_id},
        {
            "$push": {"messages": {"$each": [m.para_dict() for m in mensagens_novas]}},
            "$set":  {"updated_at": datetime.now(timezone.utc)},
        }
    )


def inserir_resumo(resumo: str, session_id: str) -> None:
    logger.info(f"Salvando resumo da sessão para session_id: {session_id}")

    collection.update_one(
        {"session_id": session_id},
        {"$set": {"resume": resumo}}
    )


def encerrar_sessao(session_id: str) -> str:
    logger.info("Encerrando sessão do usuário e gerando resumo da sessão...")

    doc = collection.find_one({"session_id": session_id})

    if not doc or not doc.get("messages"):
        return ""

    resumo = _gerar_resumo(doc["messages"])
    inserir_resumo(resumo, session_id)

    return resumo

from datetime import UTC, datetime

import assessor_ai.tools.mongo.users.core as users
from assessor_ai.tools.mongo.chats.schemas import ChatDocument, Mensagem
from assessor_ai.tools.mongo.connection import banco
from assessor_ai.tools.mongo.helpers import _gerar_perfil, _gerar_resumo
from config.logging import get_logger

logger = get_logger(__name__)

collection = banco["chats"]


def criar(user_id: str, session_id: str, mensagens: list[Mensagem]) -> None:
    logger.info(f"Criando novo chat para session_id: {session_id}")

    document = ChatDocument(
        user_id=user_id,
        session_id=session_id,
        messages=[m.para_dict() for m in mensagens],
    )
    collection.insert_one(document.model_dump())


def listar_por_usuario(user_id: str, limit: int = 50) -> list[dict]:
    logger.info(f"Listando chats para user_id: {user_id}")

    cursor = (
        collection.find({"user_id": user_id}, {"messages": {"$slice": 1}})
        .sort("updated_at", -1)
        .limit(limit)
    )
    return list(cursor)


def buscar(session_id: str, limit: int = 5, user_id: str | None = None) -> dict | None:
    logger.info(f"Buscando histórico de mensagens para session_id: {session_id} (limit={limit})")

    filtro = {"session_id": session_id}
    if user_id is not None:
        filtro["user_id"] = user_id

    return collection.find_one(
        filtro,
        {"messages": {"$slice": -limit}}
    )


def atualizar_mensagens(session_id: str, mensagens_novas: list[Mensagem]) -> None:
    logger.info(f"Adicionando mensagens para session_id: {session_id}")

    collection.update_one(
        {"session_id": session_id},
        {
            "$push": {"messages": {"$each": [m.para_dict() for m in mensagens_novas]}},
            "$set":  {"updated_at": datetime.now(UTC)},
        }
    )


def inserir_resumo(resumo: str, session_id: str) -> None:
    logger.info(f"Salvando resumo da sessão para session_id: {session_id}")

    collection.update_one(
        {"session_id": session_id},
        {"$set": {"resume": resumo}}
    )


def encerrar_sessao(session_id: str, user_id: str) -> None:
    logger.info(f"Encerrando sessão para session_id: {session_id}")

    doc = collection.find_one({"session_id": session_id})

    if not doc or not doc.get("messages"):
        return

    resumo = _gerar_resumo(doc["messages"])
    inserir_resumo(resumo, session_id)

    usuario = users.buscar(user_id)
    perfil_atual = usuario.get("profile", "") if usuario else ""

    perfil_atualizado = _gerar_perfil(perfil_atual, resumo)
    users.atualizar_perfil(user_id, perfil_atualizado)
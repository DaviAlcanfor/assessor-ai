"""Persistência do histórico de conversas (Mongo), sem regra de negócio. Síncrono: o service chama com
`asyncio.to_thread`. Quem redige PII pro LangSmith e converte as mensagens é `services/chat_service.py`."""

from datetime import UTC, datetime
from typing import cast

from app.domain.models.chat_store import ChatDocument, ChatRecord, Mensagem
from app.domain.types import ChatID, UserID
from app.infra.logging import Logging
from app.infra.mongo import MongoRepo

logger = Logging.get_logger("chats")


class ChatRepository(MongoRepo[ChatRecord]):
    collection_name = "chats"

    def criar(self, user_id: UserID, session_id: ChatID, mensagens: list[Mensagem]) -> None:
        logger.info(f"Criando novo chat para session_id: {session_id}")

        document = ChatDocument(
            user_id=user_id,
            session_id=session_id,
            messages=[m.para_dict() for m in mensagens],
        )
        self.collection.insert_one(cast("ChatRecord", document.model_dump()))

    def listar_por_usuario(self, user_id: UserID, limit: int = 50) -> list[ChatRecord]:
        logger.info(f"Listando chats para user_id: {user_id}")

        cursor = (
            self.collection.find({"user_id": user_id}, {"messages": {"$slice": 1}})
            .sort("updated_at", -1)
            .limit(limit)
        )
        return list(cursor)

    def buscar(
        self, session_id: ChatID, limit: int | None = 5, user_id: UserID | None = None
    ) -> ChatRecord | None:
        logger.info(f"Buscando histórico de mensagens para session_id: {session_id} (limit={limit})")

        filtro: dict[str, object] = {"session_id": session_id}
        if user_id is not None:
            filtro["user_id"] = user_id

        # limit=None → sem `$slice`, devolve o histórico inteiro (é o que `buscar_historico`
        # usa pra montar a resposta de GET /v1/chats/{id}/messages; truncar em 5 aqui fazia a
        # tela do chat sempre mostrar só as últimas 5 mensagens de qualquer conversa).
        projecao = {"messages": {"$slice": -limit}} if limit is not None else {}

        return self.collection.find_one(filtro, projecao)

    def atualizar_mensagens(self, session_id: ChatID, mensagens_novas: list[Mensagem]) -> None:
        logger.info(f"Adicionando mensagens para session_id: {session_id}")

        self.collection.update_one(
            {"session_id": session_id},
            {
                "$push": {"messages": {"$each": [m.para_dict() for m in mensagens_novas]}},
                "$set":  {"updated_at": datetime.now(UTC)},
            },
        )

    def inserir_resumo(self, resumo: str, session_id: ChatID) -> None:
        logger.info(f"Salvando resumo da sessão para session_id: {session_id}")

        self.collection.update_one({"session_id": session_id}, {"$set": {"resume": resumo}})


chat_repository = ChatRepository()


__all__ = ["ChatRepository", "chat_repository"]

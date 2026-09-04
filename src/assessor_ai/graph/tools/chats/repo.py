from datetime import UTC, datetime

from assessor_ai.graph.tools.chats.helpers import gerar_perfil, gerar_resumo
from assessor_ai.graph.tools.chats.schemas import ChatDocument, Mensagem
from assessor_ai.graph.tools.usuarios.repo import UsuariosRepo
from assessor_ai.infra.mongo import MongoConn, MongoRepo
from assessor_ai.logging import get_logger

logger = get_logger("chats")


class ChatsRepo(MongoRepo):
    """Histórico de conversas no Mongo. Repositório interno — não é tool do LLM."""

    collection_name = "chats"

    def __init__(self, conn: MongoConn | None = None, usuarios: UsuariosRepo | None = None) -> None:
        super().__init__(conn)
        self.usuarios = usuarios or UsuariosRepo(conn)

    def criar(self, user_id: str, session_id: str, mensagens: list[Mensagem]) -> None:
        logger.info(f"Criando novo chat para session_id: {session_id}")

        document = ChatDocument(
            user_id=user_id,
            session_id=session_id,
            messages=[m.para_dict() for m in mensagens],
        )
        self.collection.insert_one(document.model_dump())

    def listar_por_usuario(self, user_id: str, limit: int = 50) -> list[dict]:
        logger.info(f"Listando chats para user_id: {user_id}")

        cursor = (
            self.collection.find({"user_id": user_id}, {"messages": {"$slice": 1}})
            .sort("updated_at", -1)
            .limit(limit)
        )
        return list(cursor)

    def buscar(self, session_id: str, limit: int = 5, user_id: str | None = None) -> dict | None:
        logger.info(f"Buscando histórico de mensagens para session_id: {session_id} (limit={limit})")

        filtro = {"session_id": session_id}
        if user_id is not None:
            filtro["user_id"] = user_id

        return self.collection.find_one(filtro, {"messages": {"$slice": -limit}})

    def atualizar_mensagens(self, session_id: str, mensagens_novas: list[Mensagem]) -> None:
        logger.info(f"Adicionando mensagens para session_id: {session_id}")

        self.collection.update_one(
            {"session_id": session_id},
            {
                "$push": {"messages": {"$each": [m.para_dict() for m in mensagens_novas]}},
                "$set":  {"updated_at": datetime.now(UTC)},
            },
        )

    def inserir_resumo(self, resumo: str, session_id: str) -> None:
        logger.info(f"Salvando resumo da sessão para session_id: {session_id}")

        self.collection.update_one({"session_id": session_id}, {"$set": {"resume": resumo}})

    def encerrar_sessao(self, session_id: str, user_id: str) -> None:
        """Resume a conversa, salva o resumo e realimenta o perfil do usuário com ele."""

        logger.info(f"Encerrando sessão para session_id: {session_id}")

        doc = self.collection.find_one({"session_id": session_id})

        if not doc or not doc.get("messages"):
            return

        resumo = gerar_resumo(doc["messages"])
        self.inserir_resumo(resumo, session_id)

        usuario = self.usuarios.buscar(user_id)
        perfil_atual = usuario.get("profile", "") if usuario else ""

        self.usuarios.atualizar_perfil(user_id, gerar_perfil(perfil_atual, resumo))


__all__ = ["ChatsRepo"]

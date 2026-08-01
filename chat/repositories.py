import tools.mongo.chats.core as chats
import tools.mongo.users.core as mongo_users
import tools.postgres.users.core as pg_users
from chat.models import ChatMessage, Role
from tools.mongo.chats.schemas import Mensagem
from tools.mongo.chats.schemas import Role as MongoRole


def _para_mensagem(msg: ChatMessage) -> Mensagem:
    return Mensagem(role=MongoRole(msg.role.value), content=msg.content)


def _de_mensagem(msg: Mensagem) -> ChatMessage:
    return ChatMessage(role=Role(msg.role), content=msg.content)


def garantir_usuario(user_id: str, nome: str, email: str) -> None:
    mongo_users.garantir_usuario(user_id, nome=nome, email=email)
    pg_users.garantir_usuario(user_id)


def buscar_perfil(user_id: str) -> str:
    usuario = mongo_users.buscar(user_id)
    return usuario.get("profile", "") if usuario else ""


def buscar_historico(session_id: str) -> list[ChatMessage] | None:
    doc = chats.buscar(session_id)
    if not doc:
        return None
    return [_de_mensagem(m) for m in Mensagem.de_dict(doc["messages"])]


def salvar_mensagens(user_id: str, session_id: str, mensagens: list[ChatMessage]) -> None:
    mensagens_mongo = [_para_mensagem(m) for m in mensagens]

    if not chats.buscar(session_id):
        chats.criar(user_id, session_id, mensagens_mongo)
    else:
        chats.atualizar_mensagens(session_id, mensagens_mongo)


def encerrar_sessao(session_id: str, user_id: str) -> None:
    chats.encerrar_sessao(session_id, user_id)


__all__ = [
    "buscar_historico",
    "buscar_perfil",
    "encerrar_sessao",
    "garantir_usuario",
    "salvar_mensagens",
]

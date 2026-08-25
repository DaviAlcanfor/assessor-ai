from langsmith import traceable

import assessor_ai.tools.mongo.chats.core as chats
import assessor_ai.tools.mongo.users.core as mongo_users
import assessor_ai.tools.postgres.users.core as pg_users
from assessor_ai.agents.nodes.guardrail.entrada import anonimizar_entrada
from assessor_ai.chat.models import ChatMessage, Role
from assessor_ai.tools.mongo.chats.schemas import Mensagem
from assessor_ai.tools.mongo.chats.schemas import Role as MongoRole
from assessor_ai.tools.redis.perfil import (
    buscar_perfil_cache,
    invalidar_perfil_cache,
    salvar_perfil_cache,
)


def _para_mensagem(msg: ChatMessage) -> Mensagem:
    return Mensagem(role=MongoRole(msg.role.value), content=msg.content)


def _de_mensagem(msg: Mensagem) -> ChatMessage:
    return ChatMessage(role=Role(msg.role), content=msg.content)


def _mensagens_redigidas(mensagens: list[ChatMessage]) -> list[dict]:
    return [
        {
            "role": m.role.value, 
            "content": anonimizar_entrada(m.content)[0]
        }
        for m in mensagens
    ]


def _redigir_saida_perfil(perfil: str | None) -> dict:
    texto, _ = anonimizar_entrada(perfil or "")
    return {"perfil": texto}


def _redigir_entrada_mensagens(inputs: dict) -> dict:
    redigido = dict(inputs)

    if "mensagens" in redigido:
        redigido["mensagens"] = _mensagens_redigidas(redigido["mensagens"])

    return redigido


def _redigir_saida_historico(historico: list[ChatMessage] | None) -> dict:
    return {"mensagens": _mensagens_redigidas(historico) if historico else []}


def garantir_usuario(user_id: str, nome: str, email: str) -> None:
    mongo_users.garantir_usuario(user_id, nome=nome, email=email)
    pg_users.garantir_usuario(user_id)


@traceable(run_type="tool", name="buscar_perfil", process_outputs=_redigir_saida_perfil)
def buscar_perfil(user_id: str) -> str:
    """
    Busca o perfil do usuário no cache Redis.
    Se não estiver no cache, busca no MongoDB e salva no cache.
    """

    perfil_cache = buscar_perfil_cache(user_id)

    if perfil_cache is not None:
        return perfil_cache

    usuario = mongo_users.buscar(user_id)
    perfil = usuario.get("profile", "") if usuario else ""

    salvar_perfil_cache(user_id, perfil)
    return perfil


def buscar_usuario_existente() -> dict | None:
    return mongo_users.buscar_algum()


def buscar_usuario_por_email(email: str) -> dict | None:
    return mongo_users.buscar_por_email(email)


def listar_usuarios() -> list[dict]:
    return mongo_users.listar()


def criar_chat(user_id: str, session_id: str) -> None:
    chats.criar(user_id, session_id, [])


def listar_chats(user_id: str) -> list[dict]:
    return chats.listar_por_usuario(user_id)


def buscar_dono_chat(session_id: str) -> str | None:
    doc = chats.buscar(session_id)

    return doc["user_id"] if doc else None


@traceable(
    run_type="tool", name="buscar_historico", process_outputs=_redigir_saida_historico
)
def buscar_historico(session_id: str, user_id: str) -> list[ChatMessage] | None:
    """
    Busca o histórico de mensagens do chat no MongoDB.
    Retorna uma lista de mensagens, ou None se o chat não existir ou não pertencer a user_id.
    """
    doc = chats.buscar(session_id, user_id=user_id)

    if not doc:
        return None

    return [_de_mensagem(m) for m in Mensagem.de_dict(doc["messages"])]


@traceable(
    run_type="tool", name="salvar_mensagens", process_inputs=_redigir_entrada_mensagens
)
def salvar_mensagens(
    user_id: str, session_id: str, mensagens: list[ChatMessage]
) -> None:
    """
    Salva as mensagens do chat no MongoDB.
    Se o chat não existir, cria um novo chat com as mensagens fornecidas.
    """

    mensagens_mongo = [_para_mensagem(m) for m in mensagens]

    if not chats.buscar(session_id):
        chats.criar(user_id, session_id, mensagens_mongo)
    else:
        chats.atualizar_mensagens(session_id, mensagens_mongo)


def encerrar_sessao(session_id: str, user_id: str) -> None:
    chats.encerrar_sessao(session_id, user_id)
    invalidar_perfil_cache(user_id)


__all__ = [
    "buscar_dono_chat",
    "buscar_historico",
    "buscar_perfil",
    "buscar_usuario_existente",
    "buscar_usuario_por_email",
    "criar_chat",
    "encerrar_sessao",
    "garantir_usuario",
    "listar_chats",
    "listar_usuarios",
    "salvar_mensagens",
]

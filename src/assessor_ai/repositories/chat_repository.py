import asyncio

from langsmith import traceable

from assessor_ai.core.cache import (
    buscar_perfil_cache,
    invalidar_perfil_cache,
    salvar_perfil_cache,
)
from assessor_ai.core.privacy import anonimizar_entrada
from assessor_ai.schemas.models import ChatMessage, Role
from assessor_ai.tools import chats, usuarios
from assessor_ai.tools.chats.schemas import Mensagem
from assessor_ai.tools.chats.schemas import Role as MongoRole

# Os drivers de Mongo/Redis/SQLAlchemy usados aqui são todos síncronos e bloqueantes. Como a
# cadeia acima (service -> rotas/TUI/A2A) é async, cada chamada vai pra thread via
# `asyncio.to_thread` em vez de travar o event loop. Trocar por drivers async (motor, redis.asyncio)
# é PR à parte.


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


async def garantir_usuario(user_id: str, nome: str, email: str) -> None:
    await asyncio.to_thread(usuarios.garantir_usuario, user_id, nome=nome, email=email)


@traceable(run_type="tool", name="buscar_perfil", process_outputs=_redigir_saida_perfil)
async def buscar_perfil(user_id: str) -> str:
    """
    Busca o perfil do usuário no cache Redis.
    Se não estiver no cache, busca no MongoDB e salva no cache.
    """

    perfil_cache = await asyncio.to_thread(buscar_perfil_cache, user_id)

    if perfil_cache is not None:
        return perfil_cache

    usuario = await asyncio.to_thread(usuarios.buscar, user_id)
    perfil = usuario.get("profile", "") if usuario else ""

    await asyncio.to_thread(salvar_perfil_cache, user_id, perfil)
    return perfil


async def buscar_usuario_existente() -> dict | None:
    return await asyncio.to_thread(usuarios.buscar_algum)


async def buscar_usuario_por_email(email: str) -> dict | None:
    return await asyncio.to_thread(usuarios.buscar_por_email, email)


async def listar_usuarios() -> list[dict]:
    return await asyncio.to_thread(usuarios.listar)


async def criar_chat(user_id: str, session_id: str) -> None:
    await asyncio.to_thread(chats.criar, user_id, session_id, [])


async def listar_chats(user_id: str) -> list[dict]:
    return await asyncio.to_thread(chats.listar_por_usuario, user_id)


async def buscar_dono_chat(session_id: str) -> str | None:
    doc = await asyncio.to_thread(chats.buscar, session_id)

    return doc["user_id"] if doc else None


@traceable(
    run_type="tool", name="buscar_historico", process_outputs=_redigir_saida_historico
)
async def buscar_historico(session_id: str, user_id: str) -> list[ChatMessage] | None:
    """
    Busca o histórico de mensagens do chat no MongoDB.
    Retorna uma lista de mensagens, ou None se o chat não existir ou não pertencer a user_id.
    """
    doc = await asyncio.to_thread(chats.buscar, session_id, user_id=user_id)

    if not doc:
        return None

    return [_de_mensagem(m) for m in Mensagem.de_dict(doc["messages"])]


@traceable(
    run_type="tool", name="salvar_mensagens", process_inputs=_redigir_entrada_mensagens
)
async def salvar_mensagens(
    user_id: str, session_id: str, mensagens: list[ChatMessage]
) -> None:
    """
    Salva as mensagens do chat no MongoDB.
    Se o chat não existir, cria um novo chat com as mensagens fornecidas.
    """

    mensagens_mongo = [_para_mensagem(m) for m in mensagens]

    if not await asyncio.to_thread(chats.buscar, session_id):
        await asyncio.to_thread(chats.criar, user_id, session_id, mensagens_mongo)
    else:
        await asyncio.to_thread(chats.atualizar_mensagens, session_id, mensagens_mongo)


async def encerrar_sessao(session_id: str, user_id: str) -> None:
    await asyncio.to_thread(chats.encerrar_sessao, session_id, user_id)
    await asyncio.to_thread(invalidar_perfil_cache, user_id)


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

"""Casos de uso do chat: criar conversa, enviar mensagem (com ou sem streaming da timeline), histórico e
encerramento. É o ponto único que API, TUI, A2A e MCP usam. O armazenamento está em
`repositories/chat_repository.py` (síncrono: cada chamada vai pra thread com `to_thread`); o LLM, em
`services/runner.py`; o resumo ao encerrar, em `services/memoria_service.py`."""

import asyncio
from collections.abc import AsyncIterator
from typing import cast

from langsmith import traceable

from app.domain.errors import (
    ChatDeOutroUsuario,
    ChatNaoEncontrado,
    FalhaNoAgente,
    LimiteDeMensagensExcedido,
)
from app.domain.identifiers import novo_chat_id
from app.domain.models.chat import ChatMessage, Role
from app.domain.models.chat_store import ChatRecord, Mensagem
from app.domain.models.chat_store import Role as RoleDocumento
from app.domain.privacy import anonimizar_entrada
from app.domain.types import ChatID, UserID
from app.infra.redis.rate_limit import can_send_message
from app.repositories.chat_repository import chat_repository
from app.schemas.execution import AnswerReady, ExecutionEvent, RunFailed
from app.services import memoria_service, runner, user_service
from app.telemetry.metrics import RATE_LIMIT_REJECTIONS


def _para_mensagem(msg: ChatMessage) -> Mensagem:
    return Mensagem(role=RoleDocumento(msg.role.value), content=msg.content)


def _de_mensagem(msg: Mensagem) -> ChatMessage:
    return ChatMessage(role=Role(msg.role), content=msg.content)


def _mensagens_redigidas(mensagens: list[ChatMessage]) -> list[dict[str, str]]:
    """O LangSmith não pode receber texto de usuário cru: o trace sai com a PII anonimizada."""

    return [{"role": m.role.value, "content": anonimizar_entrada(m.content)[0]} for m in mensagens]


def _redigir_entrada_mensagens(inputs: dict[str, object]) -> dict[str, object]:
    redigido = dict(inputs)

    if "mensagens" in redigido:
        redigido["mensagens"] = _mensagens_redigidas(cast("list[ChatMessage]", redigido["mensagens"]))

    return redigido


def _redigir_saida_historico(historico: list[ChatMessage] | None) -> dict[str, list[dict[str, str]]]:
    return {"mensagens": _mensagens_redigidas(historico) if historico else []}


async def create_chat(user_id: UserID) -> ChatID:
    session_id = novo_chat_id()
    await asyncio.to_thread(chat_repository.criar, user_id, session_id, [])

    return session_id


async def obter_dono_chat(session_id: ChatID) -> UserID | None:
    doc = await asyncio.to_thread(chat_repository.buscar, session_id)

    return doc["user_id"] if doc else None


async def validar_ownership(session_id: ChatID, user_id: UserID) -> None:
    """
    Garante que o chat existe e pertence a `user_id`.
    Levanta `ChatNaoEncontrado` ou `ChatDeOutroUsuario` — quem chama decide como apresentar.
    """

    dono = await obter_dono_chat(session_id)

    if dono is None:
        raise ChatNaoEncontrado(session_id)

    if dono != user_id:
        raise ChatDeOutroUsuario(session_id)


async def listar_chats(user_id: UserID) -> list[ChatRecord]:
    return await asyncio.to_thread(chat_repository.listar_por_usuario, user_id)


async def iniciar_sessao() -> tuple[UserID, ChatID]:
    user_id = await user_service.obter_usuario_padrao()
    session_id = await create_chat(user_id)

    return user_id, session_id


@traceable(run_type="tool", name="buscar_historico", process_outputs=_redigir_saida_historico)
async def _buscar_historico(session_id: ChatID, user_id: UserID) -> list[ChatMessage] | None:
    """
    Histórico de mensagens do chat no MongoDB, ou None se o chat não existir ou não pertencer a `user_id`.
    """

    doc = await asyncio.to_thread(chat_repository.buscar, session_id, limit=None, user_id=user_id)

    if not doc:
        return None

    return [_de_mensagem(m) for m in Mensagem.de_dict(doc["messages"])]


@traceable(run_type="tool", name="salvar_mensagens", process_inputs=_redigir_entrada_mensagens)
async def _salvar_mensagens(user_id: UserID, session_id: ChatID, mensagens: list[ChatMessage]) -> None:
    """
    Salva as mensagens do chat no MongoDB. Se o chat não existir, cria um novo com elas.
    """

    mensagens_mongo = [_para_mensagem(m) for m in mensagens]

    if not await asyncio.to_thread(chat_repository.buscar, session_id):
        await asyncio.to_thread(chat_repository.criar, user_id, session_id, mensagens_mongo)
    else:
        await asyncio.to_thread(chat_repository.atualizar_mensagens, session_id, mensagens_mongo)


async def send_message(user_id: UserID, session_id: ChatID, content: str) -> str:
    """
    Envia mensagem do usuário para o chat e obtém a resposta do modelo de IA.
    """

    if not await asyncio.to_thread(can_send_message, user_id):
        RATE_LIMIT_REJECTIONS.labels(scope="user").inc()
        raise LimiteDeMensagensExcedido("Limite de mensagens por usuário excedido.")

    mensagem = ChatMessage(role=Role.HUMAN, content=content)
    perfil = await user_service.buscar_perfil(user_id)

    try:
        resposta = await runner.executar(mensagem, session_id, perfil, user_id)
    except Exception as e:
        raise FalhaNoAgente("Falha ao executar o grafo de agentes.") from e

    if not resposta:
        return "Sem resposta."

    conteudo_redigido, _ = anonimizar_entrada(content)
    novas = [
        ChatMessage(role=Role.HUMAN, content=conteudo_redigido),
        ChatMessage(role=Role.AI, content=resposta),
    ]
    await _salvar_mensagens(user_id, session_id, novas)

    return resposta


async def send_message_stream(
    user_id: UserID, session_id: ChatID, content: str
) -> AsyncIterator[ExecutionEvent]:
    """
    Mesmo fluxo de `send_message`, mas emitindo a timeline de execução em tempo real (ver
    `services/runner.py:executar_stream`). Persiste o histórico só se a execução terminar com
    sucesso — em rate limit ou falha, emite `RunFailed` e não escreve nada no Mongo.
    """

    if not await asyncio.to_thread(can_send_message, user_id):
        RATE_LIMIT_REJECTIONS.labels(scope="user").inc()
        yield RunFailed(message=LimiteDeMensagensExcedido.public_message)
        return

    mensagem = ChatMessage(role=Role.HUMAN, content=content)
    perfil = await user_service.buscar_perfil(user_id)

    resposta_final: str | None = None

    async for evento in runner.executar_stream(mensagem, session_id, perfil, user_id):
        if isinstance(evento, AnswerReady):
            resposta_final = evento.content

        yield evento

        if isinstance(evento, RunFailed):
            return

    if resposta_final is None:
        return

    conteudo_redigido, _ = anonimizar_entrada(content)
    novas = [
        ChatMessage(role=Role.HUMAN, content=conteudo_redigido),
        ChatMessage(role=Role.AI, content=resposta_final),
    ]
    await _salvar_mensagens(user_id, session_id, novas)


async def get_history(session_id: ChatID, user_id: UserID) -> list[ChatMessage] | None:
    return await _buscar_historico(session_id, user_id)


async def encerrar_sessao(session_id: ChatID, user_id: UserID) -> None:
    await memoria_service.encerrar_sessao(session_id, user_id)


__all__ = [
    "ChatDeOutroUsuario",
    "ChatNaoEncontrado",
    "FalhaNoAgente",
    "LimiteDeMensagensExcedido",
    "create_chat",
    "encerrar_sessao",
    "get_history",
    "iniciar_sessao",
    "listar_chats",
    "obter_dono_chat",
    "send_message",
    "send_message_stream",
    "validar_ownership",
]

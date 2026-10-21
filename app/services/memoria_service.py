"""Memória entre conversas: ao encerrar uma sessão, resume o que foi dito e realimenta o perfil do usuário.

Fica num service próprio (e não no `chat_service`) porque é o único ponto que chama LLM fora do grafo
(`llm_rapido` com os prompts de `graph/prompts/resumidor.md`)."""

import asyncio

from app.domain.models.chat_store import MessageDocument
from app.domain.types import ChatID, UserID
from app.graph.llm import llm_rapido
from app.graph.prompts.loader import load_sections
from app.infra.logging import Logging
from app.infra.redis.cache import invalidar_perfil_cache
from app.repositories.chat_repository import chat_repository
from app.repositories.usuario_repository import usuario_repository

log = Logging.get_logger(__name__)

_RESUMIDOR = load_sections("resumidor")


def _formatar_conversa(mensagens: list[MessageDocument]) -> str:
    return "\n".join(f"{msg['role']}: {msg['content']}" for msg in mensagens)


def gerar_resumo(mensagens: list[MessageDocument]) -> str:
    log.info("Resumindo conversa...")

    conversa = _formatar_conversa(mensagens)

    return llm_rapido.invoke(_RESUMIDOR["resumo"].format(conversa=conversa)).text.strip()


def gerar_perfil(perfil_atual: str, resumo: str) -> str:
    log.info("Atualizando perfil do usuário...")

    return llm_rapido.invoke(
        _RESUMIDOR["perfil"].format(perfil_atual=perfil_atual, resumo=resumo)
    ).text.strip()


def _encerrar(session_id: ChatID, user_id: UserID) -> None:
    """Resume a conversa, salva o resumo e realimenta o perfil do usuário com ele. Bloqueante (driver
    síncrono + `invoke` do LLM): quem chama usa `to_thread`."""

    log.info(f"Encerrando sessão para session_id: {session_id}")

    doc = chat_repository.buscar(session_id, limit=None)

    if not doc or not doc.get("messages"):
        return

    resumo = gerar_resumo(doc["messages"])
    chat_repository.inserir_resumo(resumo, session_id)

    usuario = usuario_repository.buscar(user_id)
    perfil_atual = usuario.get("profile", "") if usuario else ""

    usuario_repository.atualizar_perfil(user_id, gerar_perfil(perfil_atual, resumo))


async def encerrar_sessao(session_id: ChatID, user_id: UserID) -> None:
    await asyncio.to_thread(_encerrar, session_id, user_id)
    await asyncio.to_thread(invalidar_perfil_cache, user_id)


__all__ = ["encerrar_sessao", "gerar_perfil", "gerar_resumo"]

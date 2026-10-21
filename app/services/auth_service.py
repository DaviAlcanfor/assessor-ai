"""Quem é o usuário de uma credencial (chave de API ou sessão web). Compartilhado por todas as portas de
entrada que autenticam (rotas HTTP e MCP), pra nenhuma delas importar `graph.tools`, repositories nem infra."""

import asyncio

from app.domain.types import APIKey, CsrfToken, SessionToken, UserID
from app.infra.redis import session
from app.infra.redis.session import SessionRecord
from app.services import user_service
from app.settings import settings


async def usuario_da_chave(api_key: str | None) -> UserID | None:
    """`None` = credencial ausente ou inválida.

    Com `API__KEY_AUTH_ENABLED=false` (modo dev) não há credencial: devolve o usuário padrão, o mesmo
    bootstrap da TUI e da rota de chats."""

    if not settings.api.key_auth_enabled:
        return await user_service.obter_usuario_padrao()

    if api_key is None:
        return None

    return await user_service.buscar_user_id_por_api_key(APIKey(api_key))


async def criar_sessao(user_id: UserID) -> tuple[SessionToken, CsrfToken]:
    return await asyncio.to_thread(session.criar_sessao, user_id)


async def buscar_sessao(session_token: SessionToken) -> SessionRecord | None:
    return await asyncio.to_thread(session.buscar_sessao, session_token)


async def revogar_sessao(session_token: SessionToken) -> None:
    await asyncio.to_thread(session.revogar_sessao, session_token)


def hash_csrf(csrf_token: CsrfToken) -> str:
    return session.hash_csrf(csrf_token)


__all__ = ["buscar_sessao", "criar_sessao", "hash_csrf", "revogar_sessao", "usuario_da_chave"]

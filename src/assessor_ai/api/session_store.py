"""
Sessão web em cima do Redis — mesmo padrão de `api/limiter.py` (infra de auth, cliente Redis
direto, sem passar pelo repositório de agente). Namespace `session:*`, separado do `auth:*` que
`graph/tools/usuarios/schemas.py` usa pra API key, pra não colidir chave nem TTL.

TTL vem só do Redis (`EXPIRE`) — não duplicamos `expires_at` dentro do valor guardado.
"""

import hashlib
import secrets
from typing import cast

from pydantic import BaseModel, ConfigDict, ValidationError

from assessor_ai.config import settings
from assessor_ai.identifiers import CsrfToken, SessionToken, UserID
from assessor_ai.infra.redis import redis
from assessor_ai.logging import get_logger

logger = get_logger(__name__)


class SessionRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: UserID
    csrf_hash: str


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _chave(session_token: SessionToken) -> str:
    return f"session:{_hash(session_token)}"


def criar_sessao(user_id: UserID) -> tuple[SessionToken, CsrfToken]:
    session_token = SessionToken(secrets.token_urlsafe(32))
    csrf_token = CsrfToken(secrets.token_urlsafe(32))
    record = SessionRecord(user_id=user_id, csrf_hash=_hash(csrf_token))

    redis.client.set(_chave(session_token), record.model_dump_json(), ex=settings.SESSION_TTL_SECONDS)

    return session_token, csrf_token


def buscar_sessao(session_token: SessionToken) -> SessionRecord | None:
    chave = _chave(session_token)
    # a conexão usa decode_responses=True, então o retorno é str (stub do redis diz bytes | str)
    raw = cast("str | None", redis.client.get(chave))

    if raw is None:
        return None

    try:
        return SessionRecord.model_validate_json(raw)
    except ValidationError:
        logger.warning("Registro de sessão inválido no Redis — removendo.")
        redis.client.delete(chave)
        return None


def revogar_sessao(session_token: SessionToken) -> None:
    redis.client.delete(_chave(session_token))


def hash_csrf(csrf_token: CsrfToken) -> str:
    return _hash(csrf_token)


__all__ = [
    "SessionRecord",
    "buscar_sessao",
    "criar_sessao",
    "hash_csrf",
    "revogar_sessao",
]

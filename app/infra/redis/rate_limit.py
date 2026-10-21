"""Limite de mensagens por usuário (contador com TTL no Redis). Vale pra API, TUI, A2A e MCP igualmente:
é aplicado em `services/chat_service.py`, abaixo de todas as portas de entrada.

O limite por IP das rotas HTTP é outro, o `limiter` do slowapi em `api/limiter.py` — os dois só dividem o Redis.
"""

from app.domain.types import UserID
from app.infra.logging import Logging
from app.infra.redis.connection import redis

logger = Logging.get_logger(__name__)

CHAT_TTL_TIME = 60
N_MESSAGES_ACCEPTED = 10


def _chave_mensagem(user_id: UserID) -> str:
    return f"chat:{user_id}:message"


def can_send_message(user_id: UserID) -> bool:
    r = redis.client
    key = _chave_mensagem(user_id)

    result = r.incr(key)

    if result == 1:
        r.expire(key, CHAT_TTL_TIME)

    if result <= N_MESSAGES_ACCEPTED:
        return True

    logger.warning(f"User {user_id} has exceeded the message limit.")
    return False


__all__ = ["CHAT_TTL_TIME", "N_MESSAGES_ACCEPTED", "can_send_message"]

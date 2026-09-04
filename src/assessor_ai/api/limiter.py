"""
Dois limites independentes, que só compartilham o Redis:

- `limiter`: slowapi por IP, aplicado como decorator nas rotas HTTP.
- `can_send_message`: por `user_id`, aplicado por `services/chat_service.py` — vale pra API, TUI e A2A
  igualmente, porque mora abaixo da camada de entrega.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

from assessor_ai.config import settings
from assessor_ai.infra.redis import redis
from assessor_ai.logging import get_logger

logger = get_logger(__name__)

CHAT_TTL_TIME = 60
N_MESSAGES_ACCEPTED = 10


def _chave_mensagem(user_id: str) -> str:
    return f"chat:{user_id}:message"


# storage_uri=Redis: sem isso, cada worker/instância guarda a contagem em memória própria —
# com N workers o limite efetivo vira N vezes o configurado (bypass trivial via mais tráfego
# batendo em workers diferentes). Redis já é infra compartilhada do projeto.
# enabled: desligado no modo dev (mesmo gate da auth por API key) — os limites por rota
# (10-20/min) estrangulam o frontend local navegando entre chats.
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.REDIS_URL.get_secret_value(),
    enabled=settings.API_KEY_AUTH_ENABLED,
)


def can_send_message(user_id: str) -> bool:
    r = redis.client
    key = _chave_mensagem(user_id)

    result = r.incr(key)

    if result == 1:
        r.expire(key, CHAT_TTL_TIME)

    if result <= N_MESSAGES_ACCEPTED:
        return True

    logger.warning(f"User {user_id} has exceeded the message limit.")
    return False


__all__ = [
    "CHAT_TTL_TIME",
    "N_MESSAGES_ACCEPTED",
    "can_send_message",
    "limiter",
]

from tools.redis.connection import get_client
from config.logging import get_logger
from tools.redis.schemas import (
    CHAT_TTL_TIME,
    N_MESSAGES_ACCEPTED,
    _chave_mensagem
)


logger = get_logger(__name__)


def can_send_message(user_id: str) -> bool:
    r = get_client()
    key = _chave_mensagem(user_id)

    result = r.incr(key)

    if result == 1:
        r.expire(key, CHAT_TTL_TIME)

    if result <= N_MESSAGES_ACCEPTED:
        return True

    logger.warning(f"User {user_id} has exceeded the message limit.")
    return False


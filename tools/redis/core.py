from redis import Redis

from config.logging import get_logger
from config.settings import settings
from tools.redis.schemas import (
    API_KEY_TTL_TIME,
    CHAT_TTL_TIME,
    N_MESSAGES_ACCEPTED,
    _chave_api_key,
    _chave_api_key_lookup,
    _chave_mensagem,
    _hash_api_key,
)

logger = get_logger(__name__)
_client: Redis | None = None

def get_client() -> Redis:
    global _client

    if _client is None:
        _client = Redis.from_url(settings.REDIS_URI)

    return _client


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


def allocate_api_key(user_id: str, api_key: str) -> bool:
    r = get_client()

    hashed = _hash_api_key(api_key)

    user_key = _chave_api_key(user_id)
    lookup_key = _chave_api_key_lookup(hashed)

    if r.exists(user_key):
        logger.warning(f"API key already allocated for user {user_id}.")
        return False

    pipeline = r.pipeline()
    pipeline.set(user_key, hashed, ex=API_KEY_TTL_TIME)
    pipeline.set(lookup_key, user_id, ex=API_KEY_TTL_TIME)
    pipeline.execute()

    logger.info(f"Allocated API key for user {user_id}.")
    return True


def get_user_id_by_api_key(api_key: str) -> str | None:
    r = get_client()

    hashed = _hash_api_key(api_key)
    user_id = r.get(_chave_api_key_lookup(hashed))

    if user_id is not None:
        return user_id.decode("utf-8")

    logger.warning("API key not found.")
    return None
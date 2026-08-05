from assessor_ai.tools.redis.connection import get_client
from assessor_ai.tools.redis.schemas import (
    API_KEY_TTL_TIME,
    _chave_api_key,
    _chave_api_key_lookup,
    _hash_api_key,
)
from config.logging import get_logger

logger = get_logger(__name__)


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
        return user_id

    logger.warning("API key not found.")
    return None
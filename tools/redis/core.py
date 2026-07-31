from redis import Redis

from config.settings import settings
from config.logging import get_logger
from tools.redis.schemas import (
    API_KEY_TTL_TIME, 
    CHAT_TTL_TIME,
    N_MESSAGES_ACCEPTED,
    
    # keys
    _chave_mensagem,
    _chave_api_key,
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

    address = _chave_mensagem(user_id)
    key = r.set(address, 1, ex=CHAT_TTL_TIME, nx=True)

    if key:
        return True

    count = int(r.get(address))
    if count < N_MESSAGES_ACCEPTED:
        r.incr(address)
        return True

    logger.warning(f"User {user_id} has exceeded the message limit.")
    return False




def allocate_api_key(user_id: str, api_key: str) -> bool:
    r = get_client()
    
    address = _chave_api_key(user_id)
    key = r.set(address, api_key, ex=API_KEY_TTL_TIME, nx=True)
    
    logger.info(f"Allocated API key for user {user_id}.")
    return key is not None


def get_api_key(user_id: str) -> str | None:
    r = get_client()
    
    address = _chave_api_key(user_id)
    api_key = r.get(address)
    
    if api_key is not None:
        return api_key.decode("utf-8")
          
    logger.warning(f"API key not found for user {user_id}.")
    return None
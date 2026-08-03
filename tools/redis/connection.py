from redis import Redis
from config.settings import settings


def get_client() -> Redis:
    global _client

    if _client is None:
        _client = Redis.from_url(settings.UPSTASH_REDIS_REST_URL)

    return _client
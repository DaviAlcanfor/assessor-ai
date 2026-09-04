"""Conexão com o Redis. Client lazy — nada de I/O no import."""

from redis import Redis as RedisClient

from assessor_ai.config import settings


class RedisConn:
    def __init__(self) -> None:
        self._client: RedisClient | None = None

    @property
    def client(self) -> RedisClient:
        # decode_responses=True: o retorno vem como str, não bytes
        if self._client is None:
            self._client = RedisClient.from_url(
                settings.REDIS_URL.get_secret_value(), decode_responses=True
            )

        return self._client


redis = RedisConn()


__all__ = ["RedisConn", "redis"]

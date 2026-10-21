"""Conexão com o Redis. Client lazy — nada de I/O no import."""

from redis import Redis as RedisClient

from app.infra.base import Conector
from app.settings import settings


class RedisConn(Conector[RedisClient]):
    def __init__(self) -> None:
        self._client: RedisClient | None = None

    def conectar(self) -> RedisClient:
        if self._client is None:
            self._client = RedisClient.from_url(
                settings.database.redis_url.get_secret_value(), 
                decode_responses=True
            )

        return self._client

    @property
    def client(self) -> RedisClient:
        return self.conectar()


redis = RedisConn()


__all__ = ["RedisConn", "redis"]

"""Conexão com o Mongo. Client lazy — nada de I/O no import (ver CODE_STYLE.md)."""

from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

from assessor_ai.config import settings


class MongoConn:
    def __init__(self) -> None:
        self._client: MongoClient | None = None

    @property
    def client(self) -> MongoClient:
        if self._client is None:
            self._client = MongoClient(
                settings.MONGO_URL.get_secret_value(),
                maxPoolSize=10,
                minPoolSize=1,
                maxIdleTimeMS=60000,
                waitQueueTimeoutMS=5000,
            )

        return self._client

    @property
    def banco(self) -> Database:
        return self.client[settings.MONGO_COLLECTION_NAME]

    def collection(self, nome: str) -> Collection:
        return self.banco[nome]


mongo = MongoConn()


class MongoRepo:
    """
    Base dos repositórios de Mongo: resolve a collection uma vez, no primeiro acesso.

    Cada subclasse declara `collection_name`; o corpo dos métodos usa `self.collection`
    direto, sem passar por `banco["..."]` em cada arquivo.
    """

    collection_name: str

    def __init__(self, conn: MongoConn | None = None) -> None:
        self.conn = conn or mongo

    @property
    def collection(self) -> Collection:
        return self.conn.collection(self.collection_name)


__all__ = ["MongoConn", "MongoRepo", "mongo"]

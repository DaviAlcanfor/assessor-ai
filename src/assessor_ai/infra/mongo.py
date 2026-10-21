"""Conexão com o Mongo. Client lazy — nada de I/O no import (ver CODE_STYLE.md)."""

from collections.abc import Mapping
from typing import Any, cast

from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

from assessor_ai.config import settings
from assessor_ai.infra.base import Conector


class MongoConn(Conector[MongoClient[dict[str, Any]]]):
    def __init__(self) -> None:
        self._client: MongoClient[dict[str, Any]] | None = None

    def conectar(self) -> MongoClient[dict[str, Any]]:
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
    def client(self) -> MongoClient[dict[str, Any]]:
        return self.conectar()

    @property
    def banco(self) -> Database[dict[str, Any]]:
        return self.client[settings.MONGO_COLLECTION_NAME]

    def collection(self, nome: str) -> Collection[dict[str, Any]]:
        return self.banco[nome]


mongo = MongoConn()


class MongoRepo[DocumentT: Mapping[str, Any]]:

    collection_name: str

    def __init__(self, conn: MongoConn | None = None) -> None:
        self.conn = conn or mongo

    @property
    def collection(self) -> Collection[DocumentT]:
        return cast("Collection[DocumentT]", self.conn.collection(self.collection_name))


__all__ = ["MongoConn", "MongoRepo", "mongo"]

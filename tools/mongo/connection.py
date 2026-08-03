from pymongo import MongoClient
from pymongo.database import Database
from config.settings import settings


_client: MongoClient | None = None

def _conectar() -> Database:
    global _client
    
    if _client is None:
        _client = MongoClient(
            settings.MONGO_URL,
            maxPoolSize=10,
            minPoolSize=1,
            maxIdleTimeMS=60000,
            waitQueueTimeoutMS=5000,
        )
    return _client[settings.MONGO_COLLECTION_NAME]


banco = _conectar()
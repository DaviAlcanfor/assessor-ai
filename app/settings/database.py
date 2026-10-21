from pydantic import BaseModel, SecretStr


class DatabaseSettings(BaseModel):
    """Tudo que é URL de conexão é `SecretStr`: carrega usuário e senha embutidos."""

    postgres_url: SecretStr

    mongo_url: SecretStr
    mongo_collection_name: str

    redis_url: SecretStr

    qdrant_url: str
    qdrant_api_key: SecretStr = SecretStr("")  # só instâncias cloud exigem
    qdrant_collection_name: str

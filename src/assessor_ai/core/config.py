import os

from pydantic import SecretStr
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Tudo que é credencial é `SecretStr`, inclusive as URLs de conexão — elas carregam usuário e
    senha embutidos. `SecretStr` mascara o valor no `repr`, então um `print(settings)` ou um
    traceback que mostre o objeto não vaza segredo; pra usar o valor de verdade é preciso pedir
    explicitamente com `.get_secret_value()`.
    """

    GEMINI_API_KEY: SecretStr
    GROQ_API_KEY: SecretStr

    POSTGRES_URL: SecretStr

    REDIS_URL: SecretStr

    SIGNUP_SECRET: SecretStr

    MONGO_URL: SecretStr
    MONGO_COLLECTION_NAME: str

    QDRANT_URL: str
    QDRANT_API_KEY: SecretStr
    QDRANT_COLLECTION_NAME: str

    LANGSMITH_TRACING: bool
    LANGSMITH_API_KEY: SecretStr
    LANGSMITH_PROJECT: str

    API_KEY_AUTH_ENABLED: bool = True
    A2A_BASE_URL: str = "http://localhost:8000"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",
    }


settings = Settings()

if settings.LANGSMITH_TRACING:
    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGSMITH_API_KEY"] = settings.LANGSMITH_API_KEY.get_secret_value()
    os.environ["LANGSMITH_PROJECT"] = settings.LANGSMITH_PROJECT

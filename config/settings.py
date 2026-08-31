import os

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    GEMINI_API_KEY: str
    GROQ_API_KEY: str

    POSTGRES_URL: str

    REDIS_URL: str

    SIGNUP_SECRET: str

    MONGO_URL: str
    MONGO_COLLECTION_NAME: str

    QDRANT_URL: str
    QDRANT_API_KEY: str
    QDRANT_COLLECTION_NAME: str

    LANGSMITH_TRACING: bool
    LANGSMITH_API_KEY: str
    LANGSMITH_PROJECT: str

    # Desliga a exigência de X-API-Key em /v1/chats (deixa True em produção). Temporário — burocratiza
    # demais pro estágio atual e atrapalha o A2A entre Frigus e Assessor (ver TODO.md). Rotas
    # continuam existindo, `get_current_user` (`interfaces/api/auth.py`) só passa a reaproveitar um
    # usuário existente (mesmo bootstrap da TUI) em vez de checar a chave.
    API_KEY_AUTH_ENABLED: bool = True
    # URL pública onde a API é servida — usada só pra montar o AgentCard do A2A
    # (`interfaces/a2a/agents/card.py`), default cobre o `just dev`/`just run api` local
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
    os.environ["LANGSMITH_API_KEY"] = settings.LANGSMITH_API_KEY
    os.environ["LANGSMITH_PROJECT"] = settings.LANGSMITH_PROJECT

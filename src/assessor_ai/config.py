import os

from pydantic import BaseModel, SecretStr
from pydantic_settings import BaseSettings


class Provedor(BaseModel):
    """Chave, URL e paciência de um provider. `retries` são tentativas extras: pior caso
    `(retries + 1) * timeout_s` antes do `with_fallbacks` passar pro próximo."""

    api_key:   SecretStr = SecretStr("")
    base_url:  str | None = None
    timeout_s: float = 30.0
    retries:   int = 0


class GeminiSettings(Provedor):
    """Principal dos especialistas e do guardrail; também gera os embeddings."""

    api_key: SecretStr


class GroqSettings(Provedor):
    """Primeira reserva e o `llm_rapido`. 429 por rajada costuma passar em segundos, daí 1 retry."""

    api_key: SecretStr
    retries: int = 1


class ClaudeSettings(Provedor):
    """Opcional, fora das cadeias por padrão."""

    timeout_s: float = 60.0
    retries:   int = 1


class GatewaySettings(Provedor):
    """Vercel AI Gateway: GPT-6 Luna no fim das cadeias e JeV no guardrail e no roteador.
    Opcional: sem chave os dois ficam de fora. Luna raciocina, é mais lento."""

    base_url:  str = "https://ai-gateway.vercel.sh/v1"
    timeout_s: float = 45.0
    retries:   int = 1


class LLMSettings(BaseModel):
    gemini:  GeminiSettings
    groq:    GroqSettings
    claude:  ClaudeSettings = ClaudeSettings()
    gateway: GatewaySettings = GatewaySettings()

    # Teto por papel, acima do timeout do provider: saída curta (guardrail, roteador, JeV)
    # não espera tanto quanto um especialista.
    timeout_curto_s: float = 15.0


class Settings(BaseSettings):
    """
    Tudo que é credencial é `SecretStr`, inclusive as URLs de conexão — elas carregam usuário e
    senha embutidos. `SecretStr` mascara o valor no `repr`, então um `print(settings)` ou um
    traceback que mostre o objeto não vaza segredo; pra usar o valor de verdade é preciso pedir
    explicitamente com `.get_secret_value()`.

    O grupo `llm` vira prefixo com `__` no .env: `LLM__GEMINI__API_KEY`, `LLM__GATEWAY__TIMEOUT_S`.
    """

    llm: LLMSettings

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

    SESSION_TTL_SECONDS: int = 60 * 60 * 8
    SESSION_COOKIE_NAME: str = "__Host-assessor_session"
    CSRF_COOKIE_NAME: str = "__Host-assessor_csrf"

    SESSION_COOKIE_SECURE: bool = True

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "env_nested_delimiter": "__",
        "case_sensitive": False,
        "extra": "ignore",
    }


settings = Settings()

if settings.LANGSMITH_TRACING:
    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGSMITH_API_KEY"] = settings.LANGSMITH_API_KEY.get_secret_value()
    os.environ["LANGSMITH_PROJECT"] = settings.LANGSMITH_PROJECT

"""
Ponto de entrada da configuração: um único `Settings` com os grupos de `settings/*.py`. No .env o
grupo vira prefixo com `__`: `DATABASE__POSTGRES_URL`, `LLM__GROQ__API_KEY`, `API_KEYS__SIGNUP_SECRET`.

Tudo que é credencial é `SecretStr`: `print(settings)` ou um traceback não vazam segredo; pra usar o
valor de verdade é preciso pedir com `.get_secret_value()`. Variável com nome antigo/errado não dá
erro (`extra="ignore"`): só some — confira com `settings.model_dump()` quando algo parecer ausente.
"""

import os
from typing import Literal, Self

from pydantic import model_validator
from pydantic_settings import BaseSettings

from app.settings.api import ApiSettings
from app.settings.api_keys import ApiKeysSettings
from app.settings.database import DatabaseSettings
from app.settings.llm import LLMSettings
from app.settings.mercado import MercadoSettings
from app.settings.observability import ObservabilitySettings

Environment = Literal["local", "production"]


class Settings(BaseSettings):
    environment: Environment = "local"

    api: ApiSettings = ApiSettings()
    database: DatabaseSettings
    api_keys: ApiKeysSettings
    llm: LLMSettings
    mercado: MercadoSettings = MercadoSettings()
    observability: ObservabilitySettings = ObservabilitySettings()

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "env_nested_delimiter": "__",
        "case_sensitive": False,
        "extra": "ignore",
    }

    @model_validator(mode="after")
    def _validar_producao(self) -> Self:
        if self.environment == "production":
            if not self.api.key_auth_enabled:
                raise ValueError("API__KEY_AUTH_ENABLED precisa ser true quando ENVIRONMENT=production")
            if not self.api.session_cookie_secure:
                raise ValueError("API__SESSION_COOKIE_SECURE precisa ser true quando ENVIRONMENT=production")
            if "*" in self.api.cors_origins:
                raise ValueError('API__CORS_ORIGINS não pode conter "*" quando ENVIRONMENT=production')
        return self


settings = Settings()

if settings.observability.langsmith_tracing:
    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGSMITH_API_KEY"] = settings.observability.langsmith_api_key.get_secret_value()
    os.environ["LANGSMITH_PROJECT"] = settings.observability.langsmith_project

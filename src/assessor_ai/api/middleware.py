"""Configuração de segurança do fastapi-guard — estava solta no corpo do app FastAPI."""

from fastapi import FastAPI
from guard import SecurityConfig, SecurityMiddleware

from assessor_ai.config import settings


def security_config() -> SecurityConfig:
    return SecurityConfig(
        redis_url=settings.REDIS_URL.get_secret_value(),
        # guard limita 10 req/60s por IP e depois auto-bane o IP por 1h. Fatal pro frontend em
        # modo dev (uma navegação entre chats já dispara list + messages). Só liga em produção,
        # que é o mesmo momento em que a auth por API key volta.
        enable_rate_limiting=settings.API_KEY_AUTH_ENABLED,
        enable_cors=True,
        cors_allow_origins=["*"],
        cors_allow_methods=["GET", "POST"],
        cors_allow_headers=["*"],
        cors_allow_credentials=False,
        cors_expose_headers=["X-Custom-Header"],
    )


def adicionar_middleware(app: FastAPI) -> None:
    app.add_middleware(SecurityMiddleware, config=security_config())


__all__ = ["adicionar_middleware", "security_config"]

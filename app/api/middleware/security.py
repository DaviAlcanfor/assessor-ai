"""Configuração do fastapi-guard (headers de segurança, CORS, rate limit por IP com Redis)."""

from guard import SecurityConfig

from app.settings import settings


def security_config() -> SecurityConfig:
    return SecurityConfig(
        redis_url=settings.database.redis_url.get_secret_value(),
        # guard limita 10 req/60s por IP e depois auto-bane o IP por 1h. Fatal pro frontend em
        # modo dev (uma navegação entre chats já dispara list + messages). Só liga em produção,
        # que é o mesmo momento em que a auth por API key volta.
        enable_rate_limiting=settings.api.key_auth_enabled,
        enable_cors=True,
        cors_allow_origins=settings.api.cors_origins,
        cors_allow_methods=["GET", "POST"],
        cors_allow_headers=["*"],
        cors_allow_credentials=False,
        cors_expose_headers=["X-Custom-Header", "X-Request-ID"],
    )


__all__ = ["security_config"]

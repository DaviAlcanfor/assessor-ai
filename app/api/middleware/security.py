"""Configuração do fastapi-guard (headers de segurança, CORS, rate limit por IP com Redis)."""

from guard import SecurityConfig
from guard_core.models import ALL_DETECTION_CATEGORIES

from app.settings import settings


def security_config() -> SecurityConfig:
    return SecurityConfig(
        redis_url=settings.database.redis_url.get_secret_value(),
        # guard limita 10 req/60s por IP e depois auto-bane o IP por 1h. Fatal pro frontend em
        # modo dev (uma navegação entre chats já dispara list + messages). Só liga em produção,
        # que é o mesmo momento em que a auth por API key volta.
        enable_rate_limiting=settings.api.key_auth_enabled,
        # O proxy do FastAPI Cloud põe IPs internos (10.x) no X-Forwarded-For; a categoria "ssrf"
        # (guard 8.0.2) casa isso e devolve 400 pra toda requisição, inclusive a do Frigus por A2A.
        # Esta API não busca URL informada pelo usuário, então o resto da detecção basta.
        enabled_detection_categories=ALL_DETECTION_CATEGORIES - {"ssrf"},
        enable_cors=True,
        cors_allow_origins=settings.api.cors_origins,
        cors_allow_methods=["GET", "POST"],
        cors_allow_headers=["*"],
        cors_allow_credentials=False,
        cors_expose_headers=["X-Custom-Header", "X-Request-ID"],
    )


__all__ = ["security_config"]

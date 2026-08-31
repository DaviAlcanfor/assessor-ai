from slowapi import Limiter
from slowapi.util import get_remote_address

from config.settings import settings

# storage_uri=Redis: sem isso, cada worker/instância guarda a contagem em memória própria —
# com N workers o limite efetivo vira N vezes o configurado (bypass trivial via mais tráfego
# batendo em workers diferentes). Redis já é infra compartilhada do projeto (tools/redis).
# enabled: desligado no modo dev (mesmo gate da auth por API key) — os limites por rota
# (10-20/min) estrangulam o frontend local navegando entre chats.
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.REDIS_URL,
    enabled=settings.API_KEY_AUTH_ENABLED,
)


__all__ = ["limiter",]
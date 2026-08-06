from slowapi import Limiter
from slowapi.util import get_remote_address

from config.settings import settings

# storage_uri=Redis: sem isso, cada worker/instância guarda a contagem em memória própria —
# com N workers o limite efetivo vira N vezes o configurado (bypass trivial via mais tráfego
# batendo em workers diferentes). Redis já é infra compartilhada do projeto (tools/redis).
limiter = Limiter(key_func=get_remote_address, storage_uri=settings.REDIS_URL)


__all__ = ["limiter",]
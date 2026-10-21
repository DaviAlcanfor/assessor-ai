from fastapi import FastAPI
from prometheus_client import make_asgi_app
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.a2a import montar_rotas as montar_rotas_a2a
from app.api.errors import register_exception_handlers
from app.api.lifespan import lifespan
from app.api.limiter import limiter
from app.api.mcp import montar_mcp
from app.api.middleware import adicionar_middleware
from app.api.routes import (
    auth_router,
    categories_router,
    chats_router,
    health_router,
    keys_router,
    perfil_router,
    users_router,
)

app = FastAPI(
    title="Assessor AI",
    description="API para o Assessor AI",
    version="0.5.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
# O ignore abaixo é do stub: slowapi tipa o handler com `RateLimitExceeded` concreto e o
# Starlette exige a assinatura larga `(Request, Exception)`. Correto em runtime.
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]
register_exception_handlers(app)
adicionar_middleware(app)

# Nunca exposto publicamente num deploy real — só Prometheus/rede interna.
app.mount("/metrics", make_asgi_app(), name="metrics")

app.include_router(auth_router)
app.include_router(categories_router)
app.include_router(health_router)
app.include_router(chats_router)
app.include_router(keys_router)
app.include_router(perfil_router)
app.include_router(users_router)
montar_rotas_a2a(app)
montar_mcp(app)

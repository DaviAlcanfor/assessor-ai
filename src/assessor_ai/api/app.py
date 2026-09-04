from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from assessor_ai.a2a.main import montar_rotas as montar_rotas_a2a
from assessor_ai.api.exception_handlers import register_exception_handlers
from assessor_ai.api.lifespan import lifespan
from assessor_ai.api.limiter import limiter
from assessor_ai.api.middleware import adicionar_middleware
from assessor_ai.api.routes import (
    chats_router,
    health_router,
    keys_router,
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

app.include_router(health_router)
app.include_router(chats_router)
app.include_router(keys_router)
app.include_router(users_router)
montar_rotas_a2a(app)

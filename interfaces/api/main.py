from contextlib import asynccontextmanager

from fastapi import FastAPI
from guard import SecurityConfig, SecurityMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from assessor_ai.tools.postgres.connection import dispose_engine
from config.settings import settings
from interfaces.a2a.main import montar_rotas as montar_rotas_a2a
from interfaces.api.rate_limiting import limiter
from interfaces.api.routes import chats_router, health_router, keys_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    dispose_engine()


app = FastAPI(
    title="Assessor AI",
    description="API para o Assessor AI",
    version="0.5.0",
    lifespan=lifespan,
)

config = SecurityConfig(
    redis_url=settings.REDIS_URL,
    enable_cors=True,
    cors_allow_origins=["*"],
    cors_allow_methods=["GET", "POST"],
    cors_allow_headers=["*"],
    cors_allow_credentials=False,
    cors_expose_headers=["X-Custom-Header"],
)


app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SecurityMiddleware, config=config)


app.include_router(health_router)
app.include_router(chats_router)
app.include_router(keys_router)
montar_rotas_a2a(app)

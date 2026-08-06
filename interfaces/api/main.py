from fastapi import FastAPI
from guard import SecurityConfig, SecurityMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from config.settings import settings
from interfaces.api.rate_limiting import limiter
from interfaces.api.routes import chats_router, health_router, keys_router

app = FastAPI(
    title="Assessor AI", 
    description="API para o Assessor AI", 
    version="0.5.0"
)

config = SecurityConfig(
    redis_url=settings.REDIS_URL,
    enable_rate_limiting=True,
    rate_limit=100,
    auto_ban_duration=86400,
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
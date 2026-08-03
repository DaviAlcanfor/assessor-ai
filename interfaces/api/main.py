from fastapi import FastAPI
from interfaces.api.routes import chats_router, health_router
from interfaces.api.rate_limiting import limiter
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler


app = FastAPI(
    title="Assessor AI", 
    description="API para o Assessor AI", 
    version="0.5.0"
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


app.include_router(health_router)
app.include_router(chats_router)
from interfaces.api.routes.chats import router as chats_router
from interfaces.api.routes.health import router as health_router
from interfaces.api.routes.keys import router as keys_router

__all__ = [
    "chats_router",
    "health_router",
    "keys_router",
]
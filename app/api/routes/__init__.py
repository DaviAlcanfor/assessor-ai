from app.api.routes.health import router as health_router
from app.api.routes.v1.auth import router as auth_router
from app.api.routes.v1.categories import router as categories_router
from app.api.routes.v1.chats import router as chats_router
from app.api.routes.v1.keys import router as keys_router
from app.api.routes.v1.perfil import router as perfil_router
from app.api.routes.v1.users import router as users_router

__all__ = [
    "auth_router",
    "categories_router",
    "chats_router",
    "health_router",
    "keys_router",
    "perfil_router",
    "users_router",
]

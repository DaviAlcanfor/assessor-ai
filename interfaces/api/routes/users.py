"""
Users API routes (modo dev)

Só respondem com API_KEY_AUTH_ENABLED=false — servem a tela de login do frontend, que precisa
listar/criar usuário sem key. Com a flag ligada, viram 404 (mesmo padrão de "não existe"),
evitando enumeração de usuários em produção.
"""

from fastapi import APIRouter, HTTPException, Request, status

from assessor_ai.chat import service as chat_service
from config.settings import settings
from interfaces.api.rate_limiting import limiter
from interfaces.api.schemas.user import UserCreate, UserResponse

router = APIRouter(prefix="/v1/users", tags=["users"])


def _garantir_modo_dev() -> None:
    if settings.API_KEY_AUTH_ENABLED:
        raise HTTPException(status.HTTP_404_NOT_FOUND)


@router.get("", response_model=list[UserResponse])
@limiter.limit("20/minute")
async def list_users(request: Request):
    _garantir_modo_dev()

    return [UserResponse(**u) for u in await chat_service.listar_usuarios()]


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def create_user(request: Request, payload: UserCreate):
    _garantir_modo_dev()

    user_id = await chat_service.obter_ou_criar_usuario(payload.nome, payload.email)

    return UserResponse(user_id=user_id, nome=payload.nome, email=payload.email)

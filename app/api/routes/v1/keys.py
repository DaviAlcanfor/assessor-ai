from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.auth import generate_api_key, verify_signup_secret
from app.api.limiter import limiter
from app.domain.types import APIKey
from app.schemas.key import KeyCreate, KeyCreateResponse
from app.services import user_service

router = APIRouter(prefix="/v1/keys", tags=["keys"])


@router.post(
    "",
    response_model=KeyCreateResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_signup_secret)],
)
@limiter.limit("5/minute")
async def create_key(request: Request, payload: KeyCreate) -> KeyCreateResponse:
    user_id = await user_service.obter_ou_criar_usuario(payload.nome, payload.email)

    api_key: APIKey = generate_api_key()
    if not await user_service.alocar_api_key(user_id, api_key):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Usuário já tem uma API key ativa.",
        )

    return KeyCreateResponse(user_id=user_id, api_key=api_key)

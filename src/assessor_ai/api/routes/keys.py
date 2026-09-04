from fastapi import APIRouter, Depends, HTTPException, Request, status

from assessor_ai.api.auth import verify_signup_secret
from assessor_ai.api.gen_key import generate_api_key
from assessor_ai.core.limiter import limiter
from assessor_ai.schemas.key import KeyCreate, KeyCreateResponse
from assessor_ai.services import chat_service
from assessor_ai.tools import usuarios

router = APIRouter(prefix="/v1/keys", tags=["keys"])


@router.post(
    "",
    response_model=KeyCreateResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_signup_secret)],
)
@limiter.limit("5/minute")
async def create_key(request: Request, payload: KeyCreate):
    user_id = await chat_service.obter_ou_criar_usuario(payload.nome, payload.email)

    api_key = generate_api_key()
    if not usuarios.alocar_api_key(user_id, api_key):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Usuário já tem uma API key ativa.",
        )

    return KeyCreateResponse(user_id=user_id, api_key=api_key)

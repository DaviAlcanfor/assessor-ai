from fastapi import APIRouter, HTTPException, Request, status

from assessor_ai.chat import service as chat_service
from assessor_ai.tools.redis.api_key import allocate_api_key
from interfaces.api.gen_key import generate_api_key
from interfaces.api.rate_limiting import limiter
from interfaces.api.schemas.key import KeyCreate, KeyCreateResponse

router = APIRouter(prefix="/v1/keys", tags=["keys"])


@router.post("", response_model=KeyCreateResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def create_key(request: Request, payload: KeyCreate):
    user_id = chat_service.obter_ou_criar_usuario(payload.nome, payload.email)

    api_key = generate_api_key()
    if not allocate_api_key(user_id, api_key):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Usuário já tem uma API key ativa.",
        )

    return KeyCreateResponse(user_id=user_id, api_key=api_key)

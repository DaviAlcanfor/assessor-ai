import secrets

from fastapi import Header, HTTPException, Security, status
from fastapi.security import APIKeyHeader

from assessor_ai.chat import service as chat_service
from assessor_ai.tools.redis.api_key import get_user_id_by_api_key
from config.settings import settings

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
_signup_secret_header = APIKeyHeader(name="X-Signup-Secret")


async def get_current_user(
    api_key: str | None = Security(_api_key_header),
    x_user_id: str | None = Header(None, alias="X-User-Id"),
) -> str:
    if not settings.API_KEY_AUTH_ENABLED:
        # ponytail: bypass de auth deliberado — só vale enquanto API_KEY_AUTH_ENABLED=false.
        # Permite o frontend em modo dev escolher o usuário sem precisar de API key.
        return x_user_id or await chat_service.obter_usuario_padrao()

    if api_key is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid API key")

    user_id = get_user_id_by_api_key(api_key)

    if user_id is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid API key")

    return user_id


def verify_signup_secret(secret: str = Security(_signup_secret_header)) -> None:
    if not secrets.compare_digest(secret, settings.SIGNUP_SECRET):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid signup secret")

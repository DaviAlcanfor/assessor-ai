import secrets

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from assessor_ai.chat import service as chat_service
from assessor_ai.tools.redis.api_key import get_user_id_by_api_key
from config.settings import settings

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
_signup_secret_header = APIKeyHeader(name="X-Signup-Secret")


def get_current_user(api_key: str | None = Security(_api_key_header)) -> str:
    if not settings.API_KEY_AUTH_ENABLED:
        return chat_service.obter_usuario_padrao()

    if api_key is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid API key")

    user_id = get_user_id_by_api_key(api_key)

    if user_id is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid API key")

    return user_id


def verify_signup_secret(secret: str = Security(_signup_secret_header)) -> None:
    if not secrets.compare_digest(secret, settings.SIGNUP_SECRET):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid signup secret")

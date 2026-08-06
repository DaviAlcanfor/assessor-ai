import secrets

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from assessor_ai.tools.redis.api_key import get_user_id_by_api_key
from config.settings import settings

_api_key_header = APIKeyHeader(name="X-API-Key")
_signup_secret_header = APIKeyHeader(name="X-Signup-Secret")


def get_current_user(api_key: str = Security(_api_key_header)) -> str:
    user_id = get_user_id_by_api_key(api_key)

    if user_id is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid API key")

    return user_id


def verify_signup_secret(secret: str = Security(_signup_secret_header)) -> None:
    if not secrets.compare_digest(secret, settings.SIGNUP_SECRET):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid signup secret")

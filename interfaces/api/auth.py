from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from assessor_ai.tools.redis.api_key import get_user_id_by_api_key

_api_key_header = APIKeyHeader(name="X-API-Key")


def get_current_user(api_key: str = Security(_api_key_header)) -> str:
    user_id = get_user_id_by_api_key(api_key)

    if user_id is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid API key")

    return user_id

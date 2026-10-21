import secrets

from app.domain.types import APIKey


def generate_api_key() -> APIKey:
    return APIKey(secrets.token_urlsafe(32))
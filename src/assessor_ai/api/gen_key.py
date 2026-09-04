import secrets

from assessor_ai.identifiers import APIKey


def generate_api_key() -> APIKey:
    return APIKey(secrets.token_urlsafe(32))
import secrets
import bcrypt

def generate_api_key() -> str:
    return secrets.token_urlsafe(32)
from pydantic import BaseModel


class ApiSettings(BaseModel):
    # False = modo dev: sem API key, sem rate limit do guard, usuário padrão por request.
    key_auth_enabled: bool = True
    cors_origins: list[str] = ["*"]
    a2a_base_url: str = "http://localhost:8000"

    session_ttl_seconds: int = 60 * 60 * 8
    session_cookie_name: str = "__Host-assessor_session"
    csrf_cookie_name: str = "__Host-assessor_csrf"
    session_cookie_secure: bool = True

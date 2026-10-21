from pydantic import BaseModel


class ApiSettings(BaseModel):
    # False = modo dev: sem API key, sem rate limit do guard, usuário padrão por request.
    key_auth_enabled: bool = True
    cors_origins: list[str] = ["*"]
    a2a_base_url: str = "http://localhost:8000"

    # Proteção contra DNS rebinding do servidor MCP: ele recusa (421) qualquer `Host` fora desta lista.
    # Em deploy, ponha o domínio público: API__MCP_ALLOWED_HOSTS=["meuapp.exemplo.com"].
    mcp_allowed_hosts: list[str] = ["localhost:*", "127.0.0.1:*", "[::1]:*"]
    mcp_allowed_origins: list[str] = []  # cliente MCP de desktop não manda `Origin`; navegador manda

    session_ttl_seconds: int = 60 * 60 * 8
    session_cookie_name: str = "__Host-assessor_session"
    csrf_cookie_name: str = "__Host-assessor_csrf"
    session_cookie_secure: bool = True

"""Autenticação das rotas HTTP: dependências do FastAPI (`dependencies.py`) e geração de API key (`keys.py`)."""

from app.api.auth.dependencies import (
    CsrfDep,
    CurrentPrincipalDep,
    SessionCookieDep,
    get_current_principal,
    get_current_user,
    validar_csrf_request,
    verify_signup_secret,
)
from app.api.auth.keys import generate_api_key

__all__ = [
    "CsrfDep",
    "CurrentPrincipalDep",
    "SessionCookieDep",
    "generate_api_key",
    "get_current_principal",
    "get_current_user",
    "validar_csrf_request",
    "verify_signup_secret",
]

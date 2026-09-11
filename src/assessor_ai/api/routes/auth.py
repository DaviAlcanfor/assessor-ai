"""
Sessão web (cookie + CSRF) ao lado da API key. `POST /session` troca uma API key válida (ou o
bypass de dev) por um cookie de sessão — pensado pro frontend, que hoje manda `X-API-Key` direto
de JS; a sessão evita isso, o cookie é `HttpOnly`.
"""

from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from assessor_ai.api import session_store
from assessor_ai.api.auth import (
    CsrfDep,
    CurrentPrincipalDep,
    SessionCookieDep,
    get_current_user,
)
from assessor_ai.config import settings
from assessor_ai.identifiers import SessionToken, UserID
from assessor_ai.schemas.auth import CurrentPrincipalResponse, SessionCreateResponse

router = APIRouter(prefix="/v1/auth", tags=["auth"])


def _set_session_cookies(response: Response, session_token: str, csrf_token: str) -> None:
    response.set_cookie(
        settings.SESSION_COOKIE_NAME,
        session_token,
        max_age=settings.SESSION_TTL_SECONDS,
        path="/",
        secure=settings.SESSION_COOKIE_SECURE,
        httponly=True,
        samesite="lax",
    )
    
    response.set_cookie(
        settings.CSRF_COOKIE_NAME,
        csrf_token,
        max_age=settings.SESSION_TTL_SECONDS,
        path="/",
        secure=settings.SESSION_COOKIE_SECURE,
        httponly=False,
        samesite="lax",
    )


@router.post("/session", status_code=status.HTTP_201_CREATED)
async def create_session(
    response: Response, user_id: Annotated[UserID, Depends(get_current_user)]
) -> SessionCreateResponse:
    session_token, csrf_token = session_store.criar_sessao(user_id)
    _set_session_cookies(response, session_token, csrf_token)

    expires_at = datetime.now(UTC) + timedelta(seconds=settings.SESSION_TTL_SECONDS)
    return SessionCreateResponse(user_id=user_id, expires_at=expires_at)


@router.get("/me")
async def get_me(principal: CurrentPrincipalDep) -> CurrentPrincipalResponse:
    return CurrentPrincipalResponse(user_id=principal.user_id, auth_method=principal.auth_method)


@router.delete("/session", status_code=status.HTTP_204_NO_CONTENT, dependencies=[CsrfDep])
async def delete_session(response: Response, session_token: SessionCookieDep) -> None:
    if session_token is not None:
        session_store.revogar_sessao(SessionToken(session_token))

    response.delete_cookie(settings.SESSION_COOKIE_NAME, path="/")
    response.delete_cookie(settings.CSRF_COOKIE_NAME, path="/")


__all__ = ["router"]

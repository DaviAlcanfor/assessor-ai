import secrets
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Security, status
from fastapi.security import APIKeyCookie, APIKeyHeader

from assessor_ai.api import session_store
from assessor_ai.config import settings
from assessor_ai.graph.tools import usuarios
from assessor_ai.identifiers import APIKey, CsrfToken, SessionToken, UserID
from assessor_ai.schemas.auth import AuthMethod, Principal
from assessor_ai.services import chat_service

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
_session_cookie = APIKeyCookie(name=settings.SESSION_COOKIE_NAME, auto_error=False)
_signup_secret_header = APIKeyHeader(name="X-Signup-Secret")

SessionCookieDep = Annotated[str | None, Security(_session_cookie)]


async def _resolve_principal(
    api_key: str | None, session_token: str | None, x_user_id: str | None
) -> Principal:
    if not settings.API_KEY_AUTH_ENABLED:
        # ponytail: bypass de auth deliberado — só vale enquanto API_KEY_AUTH_ENABLED=false.
        # Permite o frontend em modo dev escolher o usuário sem precisar de API key.
        user_id = UserID(x_user_id) if x_user_id else await chat_service.obter_usuario_padrao()
        return Principal(user_id=user_id, auth_method=AuthMethod.DEV)

    if api_key is not None:
        user_id_da_key = usuarios.user_id_por_api_key(APIKey(api_key))

        if user_id_da_key is None:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid API key")

        return Principal(user_id=user_id_da_key, auth_method=AuthMethod.API_KEY)

    if isinstance(session_token, str):
        record = session_store.buscar_sessao(SessionToken(session_token))

        if record is None:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired session")

        return Principal(
            user_id=record.user_id, auth_method=AuthMethod.SESSION, csrf_hash=record.csrf_hash
        )

    raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid API key")


async def get_current_principal(
    api_key: str | None = Security(_api_key_header),
    session_token: SessionCookieDep = None,
    x_user_id: str | None = Header(None, alias="X-User-Id"),
) -> Principal:
    return await _resolve_principal(api_key, session_token, x_user_id)


CurrentPrincipalDep = Annotated[Principal, Depends(get_current_principal)]


async def get_current_user(
    api_key: str | None = Security(_api_key_header),
    x_user_id: str | None = Header(None, alias="X-User-Id"),
    session_token: SessionCookieDep = None,
) -> UserID:
    principal = await _resolve_principal(api_key, session_token, x_user_id)
    return principal.user_id


async def validar_csrf_request(
    principal: CurrentPrincipalDep,
    x_csrf_token: Annotated[str | None, Header(alias="X-CSRF-Token")] = None,
) -> None:
    """
    Só se aplica à sessão via cookie — API key vai em header custom, que um form/navegação
    cross-site não consegue montar sozinho, então já é imune a CSRF por natureza.
    """

    if principal.auth_method is not AuthMethod.SESSION:
        return

    if principal.csrf_hash is None or x_csrf_token is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Missing or invalid CSRF token")

    csrf_hash_recebido = session_store.hash_csrf(CsrfToken(x_csrf_token))

    if not secrets.compare_digest(csrf_hash_recebido, principal.csrf_hash):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Missing or invalid CSRF token")


CsrfDep = Depends(validar_csrf_request)


def verify_signup_secret(secret: str = Security(_signup_secret_header)) -> None:
    if not secrets.compare_digest(secret, settings.SIGNUP_SECRET.get_secret_value()):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid signup secret")

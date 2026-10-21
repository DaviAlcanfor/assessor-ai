import pytest
from fastapi import HTTPException

from app.api.auth import dependencies as auth
from app.domain.types import CsrfToken
from app.infra.redis.session import SessionRecord
from app.repositories.usuario_repository import usuario_repository
from app.schemas.auth import AuthMethod, Principal
from app.services import auth_service


def _async(valor):
    async def _fn(*_args, **_kwargs):
        return valor

    return _fn


async def test_get_current_user_retorna_user_id_para_chave_valida(monkeypatch):
    monkeypatch.setattr(usuario_repository, "user_id_por_api_key", lambda api_key: "user-1")

    assert await auth.get_current_user(api_key="chave-valida") == "user-1"


async def test_get_current_user_rejeita_chave_invalida(monkeypatch):
    monkeypatch.setattr(usuario_repository, "user_id_por_api_key", lambda api_key: None)

    with pytest.raises(HTTPException) as exc_info:
        await auth.get_current_user(api_key="chave-invalida")

    assert exc_info.value.status_code == 401


async def test_get_current_user_rejeita_chave_ausente(monkeypatch):
    with pytest.raises(HTTPException) as exc_info:
        await auth.get_current_user(api_key=None)

    assert exc_info.value.status_code == 401


async def test_get_current_user_com_auth_desligada_ignora_chave(monkeypatch):
    monkeypatch.setattr(auth.settings.api, "key_auth_enabled", False)
    monkeypatch.setattr(auth.user_service, "obter_usuario_padrao", _async("user-padrao"))

    assert await auth.get_current_user(api_key=None, x_user_id=None) == "user-padrao"


async def test_get_current_user_com_auth_desligada_usa_x_user_id_se_vier(monkeypatch):
    monkeypatch.setattr(auth.settings.api, "key_auth_enabled", False)
    monkeypatch.setattr(auth.user_service, "obter_usuario_padrao", _async("user-padrao"))

    assert await auth.get_current_user(api_key=None, x_user_id="user-escolhido") == "user-escolhido"


async def test_get_current_user_com_auth_ligada_ignora_x_user_id(monkeypatch):
    monkeypatch.setattr(usuario_repository, "user_id_por_api_key", lambda api_key: "user-1")

    assert await auth.get_current_user(api_key="chave-valida", x_user_id="user-outro") == "user-1"


async def test_get_current_principal_via_sessao_valida(monkeypatch):
    record = SessionRecord(user_id="user-1", csrf_hash="hash-qualquer")

    async def buscar_sessao(token):
        return record

    monkeypatch.setattr(auth_service, "buscar_sessao", buscar_sessao)

    principal = await auth.get_current_principal(api_key=None, session_token="token-valido")

    assert principal.user_id == "user-1"
    assert principal.auth_method == AuthMethod.SESSION
    assert principal.csrf_hash == "hash-qualquer"


async def test_get_current_principal_rejeita_sessao_invalida(monkeypatch):
    async def sem_sessao(token):
        return None

    monkeypatch.setattr(auth_service, "buscar_sessao", sem_sessao)

    with pytest.raises(HTTPException) as exc_info:
        await auth.get_current_principal(api_key=None, session_token="token-invalido")

    assert exc_info.value.status_code == 401


async def test_get_current_principal_sem_nenhuma_credencial(monkeypatch):
    with pytest.raises(HTTPException) as exc_info:
        await auth.get_current_principal(api_key=None, session_token=None)

    assert exc_info.value.status_code == 401


async def test_validar_csrf_ignora_auth_por_api_key(monkeypatch):
    principal = Principal(user_id="user-1", auth_method=AuthMethod.API_KEY)

    # não levanta — CSRF só se aplica a AuthMethod.SESSION
    await auth.validar_csrf_request(principal=principal, x_csrf_token=None)


async def test_validar_csrf_rejeita_sessao_sem_token(monkeypatch):
    principal = Principal(user_id="user-1", auth_method=AuthMethod.SESSION, csrf_hash="hash")

    with pytest.raises(HTTPException) as exc_info:
        await auth.validar_csrf_request(principal=principal, x_csrf_token=None)

    assert exc_info.value.status_code == 403


async def test_validar_csrf_aceita_token_correto(monkeypatch):
    csrf_hash = auth_service.hash_csrf(CsrfToken("token-csrf"))
    principal = Principal(user_id="user-1", auth_method=AuthMethod.SESSION, csrf_hash=csrf_hash)

    await auth.validar_csrf_request(principal=principal, x_csrf_token="token-csrf")


async def test_validar_csrf_rejeita_token_errado(monkeypatch):
    principal = Principal(user_id="user-1", auth_method=AuthMethod.SESSION, csrf_hash="hash-certo")

    with pytest.raises(HTTPException) as exc_info:
        await auth.validar_csrf_request(principal=principal, x_csrf_token="token-errado")

    assert exc_info.value.status_code == 403

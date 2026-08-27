import pytest
from fastapi import HTTPException

from interfaces.api import auth


def _async(valor):
    async def _fn(*_args, **_kwargs):
        return valor

    return _fn


async def test_get_current_user_retorna_user_id_para_chave_valida(monkeypatch):
    monkeypatch.setattr(auth, "get_user_id_by_api_key", lambda api_key: "user-1")

    assert await auth.get_current_user(api_key="chave-valida") == "user-1"


async def test_get_current_user_rejeita_chave_invalida(monkeypatch):
    monkeypatch.setattr(auth, "get_user_id_by_api_key", lambda api_key: None)

    with pytest.raises(HTTPException) as exc_info:
        await auth.get_current_user(api_key="chave-invalida")

    assert exc_info.value.status_code == 401


async def test_get_current_user_rejeita_chave_ausente(monkeypatch):
    with pytest.raises(HTTPException) as exc_info:
        await auth.get_current_user(api_key=None)

    assert exc_info.value.status_code == 401


async def test_get_current_user_com_auth_desligada_ignora_chave(monkeypatch):
    monkeypatch.setattr(auth.settings, "API_KEY_AUTH_ENABLED", False)
    monkeypatch.setattr(auth.chat_service, "obter_usuario_padrao", _async("user-padrao"))

    assert await auth.get_current_user(api_key=None, x_user_id=None) == "user-padrao"


async def test_get_current_user_com_auth_desligada_usa_x_user_id_se_vier(monkeypatch):
    monkeypatch.setattr(auth.settings, "API_KEY_AUTH_ENABLED", False)
    monkeypatch.setattr(auth.chat_service, "obter_usuario_padrao", _async("user-padrao"))

    assert await auth.get_current_user(api_key=None, x_user_id="user-escolhido") == "user-escolhido"


async def test_get_current_user_com_auth_ligada_ignora_x_user_id(monkeypatch):
    monkeypatch.setattr(auth, "get_user_id_by_api_key", lambda api_key: "user-1")

    assert await auth.get_current_user(api_key="chave-valida", x_user_id="user-outro") == "user-1"

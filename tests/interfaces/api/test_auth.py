import pytest
from fastapi import HTTPException

from interfaces.api import auth


def test_get_current_user_retorna_user_id_para_chave_valida(monkeypatch):
    monkeypatch.setattr(auth, "get_user_id_by_api_key", lambda api_key: "user-1")

    assert auth.get_current_user(api_key="chave-valida") == "user-1"


def test_get_current_user_rejeita_chave_invalida(monkeypatch):
    monkeypatch.setattr(auth, "get_user_id_by_api_key", lambda api_key: None)

    with pytest.raises(HTTPException) as exc_info:
        auth.get_current_user(api_key="chave-invalida")

    assert exc_info.value.status_code == 401

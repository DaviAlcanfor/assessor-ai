from assessor_ai.api import session_store
from assessor_ai.api.app import app
from assessor_ai.api.auth import get_current_user
from assessor_ai.config import settings
from tests.fakes import ConnFake, FakeRedis


def _autenticar_com_api_key(user_id: str):
    app.dependency_overrides[get_current_user] = lambda: user_id


def test_create_session_seta_cookies_e_retorna_user_id(client, monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(session_store, "redis", ConnFake(fake))
    _autenticar_com_api_key("user-1")

    resposta = client.post("/v1/auth/session")

    assert resposta.status_code == 201
    assert resposta.json()["user_id"] == "user-1"
    assert settings.SESSION_COOKIE_NAME in resposta.cookies
    assert settings.CSRF_COOKIE_NAME in resposta.cookies


def test_me_retorna_principal_da_sessao(client, monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(session_store, "redis", ConnFake(fake))
    _autenticar_com_api_key("user-1")

    criada = client.post("/v1/auth/session")
    session_cookie = criada.cookies[settings.SESSION_COOKIE_NAME]

    # limpa o override de API key pra provar que /me está autenticando pela sessão, não por ele
    app.dependency_overrides.clear()

    resposta = client.get("/v1/auth/me", cookies={settings.SESSION_COOKIE_NAME: session_cookie})

    assert resposta.status_code == 200
    assert resposta.json() == {"user_id": "user-1", "auth_method": "session"}


def test_delete_session_sem_csrf_e_rejeitado(client, monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(session_store, "redis", ConnFake(fake))
    _autenticar_com_api_key("user-1")

    criada = client.post("/v1/auth/session")
    session_cookie = criada.cookies[settings.SESSION_COOKIE_NAME]
    app.dependency_overrides.clear()

    resposta = client.delete(
        "/v1/auth/session", cookies={settings.SESSION_COOKIE_NAME: session_cookie}
    )

    assert resposta.status_code == 403


def test_delete_session_com_csrf_revoga_e_retorna_204(client, monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(session_store, "redis", ConnFake(fake))
    _autenticar_com_api_key("user-1")

    criada = client.post("/v1/auth/session")
    session_cookie = criada.cookies[settings.SESSION_COOKIE_NAME]
    csrf_cookie = criada.cookies[settings.CSRF_COOKIE_NAME]
    app.dependency_overrides.clear()

    resposta = client.delete(
        "/v1/auth/session",
        cookies={settings.SESSION_COOKIE_NAME: session_cookie, settings.CSRF_COOKIE_NAME: csrf_cookie},
        headers={"X-CSRF-Token": csrf_cookie},
    )

    assert resposta.status_code == 204

    resposta_me = client.get(
        "/v1/auth/me", cookies={settings.SESSION_COOKIE_NAME: session_cookie}
    )
    assert resposta_me.status_code == 401

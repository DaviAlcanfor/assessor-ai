import pytest

import assessor_ai.chat.service as chat_service
import interfaces.api.routes.keys as keys_route
from config.settings import settings
from interfaces.api.auth import verify_signup_secret
from interfaces.api.main import app


@pytest.fixture(autouse=True)
def _sem_signup_secret(client):
    app.dependency_overrides[verify_signup_secret] = lambda: None
    yield
    app.dependency_overrides.pop(verify_signup_secret, None)


def test_create_key_sucesso(client, monkeypatch):
    monkeypatch.setattr(chat_service, "obter_ou_criar_usuario", lambda nome, email: "user-1")
    monkeypatch.setattr(keys_route, "generate_api_key", lambda: "chave-gerada")
    monkeypatch.setattr(keys_route, "allocate_api_key", lambda user_id, api_key: True)

    resposta = client.post(
        "/v1/keys", json={"nome": "Davi", "email": "davi@example.com"}
    )

    assert resposta.status_code == 201
    assert resposta.json() == {"user_id": "user-1", "api_key": "chave-gerada"}


def test_create_key_usuario_ja_tem_chave_retorna_409(client, monkeypatch):
    monkeypatch.setattr(chat_service, "obter_ou_criar_usuario", lambda nome, email: "user-1")
    monkeypatch.setattr(keys_route, "generate_api_key", lambda: "chave-gerada")
    monkeypatch.setattr(keys_route, "allocate_api_key", lambda user_id, api_key: False)

    resposta = client.post(
        "/v1/keys", json={"nome": "Davi", "email": "davi@example.com"}
    )

    assert resposta.status_code == 409


def test_create_key_email_vazio_e_rejeitado_pelo_schema(client):
    resposta = client.post("/v1/keys", json={"nome": "Davi", "email": ""})

    assert resposta.status_code == 422


def test_create_key_sem_signup_secret_e_rejeitado(client):
    app.dependency_overrides.pop(verify_signup_secret, None)

    resposta = client.post("/v1/keys", json={"nome": "Davi", "email": "davi@example.com"})

    assert resposta.status_code == 401


def test_create_key_signup_secret_invalido_e_rejeitado(client):
    app.dependency_overrides.pop(verify_signup_secret, None)

    resposta = client.post(
        "/v1/keys",
        json={"nome": "Davi", "email": "davi@example.com"},
        headers={"X-Signup-Secret": "secret-errado"},
    )

    assert resposta.status_code == 401


def test_create_key_signup_secret_valido_segue_fluxo(client, monkeypatch):
    app.dependency_overrides.pop(verify_signup_secret, None)
    monkeypatch.setattr(chat_service, "obter_ou_criar_usuario", lambda nome, email: "user-1")
    monkeypatch.setattr(keys_route, "generate_api_key", lambda: "chave-gerada")
    monkeypatch.setattr(keys_route, "allocate_api_key", lambda user_id, api_key: True)

    resposta = client.post(
        "/v1/keys",
        json={"nome": "Davi", "email": "davi@example.com"},
        headers={"X-Signup-Secret": settings.SIGNUP_SECRET},
    )

    assert resposta.status_code == 201

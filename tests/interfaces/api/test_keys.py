import assessor_ai.chat.service as chat_service
import interfaces.api.routes.keys as keys_route


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

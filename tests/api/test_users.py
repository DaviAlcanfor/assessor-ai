from app.api.routes.v1 import users as users_route
from app.services import user_service


def _async(valor):
    """Stub async: `user_service` virou corrotina, o monkeypatch precisa devolver uma."""

    async def _fn(*_args, **_kwargs):
        return valor

    return _fn



def test_list_users_com_auth_ligada_retorna_404(client, monkeypatch):
    monkeypatch.setattr(users_route.settings.api, "key_auth_enabled", True)

    resposta = client.get("/v1/users")

    assert resposta.status_code == 404


def test_create_user_com_auth_ligada_retorna_404(client, monkeypatch):
    monkeypatch.setattr(users_route.settings.api, "key_auth_enabled", True)

    resposta = client.post("/v1/users", json={"nome": "Ana", "email": "ana@example.com"})

    assert resposta.status_code == 404


def test_list_users_com_auth_desligada_lista_usuarios(client, monkeypatch):
    monkeypatch.setattr(users_route.settings.api, "key_auth_enabled", False)
    monkeypatch.setattr(
        user_service,
        "listar_usuarios",
        _async([{"user_id": "u1", "nome": "Ana", "email": "ana@example.com"}]),
    )

    resposta = client.get("/v1/users")

    assert resposta.status_code == 200
    assert resposta.json() == [{"user_id": "u1", "nome": "Ana", "email": "ana@example.com"}]


def test_create_user_com_auth_desligada_cria_usuario(client, monkeypatch):
    monkeypatch.setattr(users_route.settings.api, "key_auth_enabled", False)
    monkeypatch.setattr(user_service, "obter_ou_criar_usuario", _async("novo-id"))

    resposta = client.post("/v1/users", json={"nome": "Ana", "email": "ana@example.com"})

    assert resposta.status_code == 201
    assert resposta.json() == {"user_id": "novo-id", "nome": "Ana", "email": "ana@example.com"}

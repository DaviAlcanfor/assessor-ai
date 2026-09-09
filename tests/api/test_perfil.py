from assessor_ai.api.app import app
from assessor_ai.api.auth import get_current_user
from assessor_ai.services import chat_service

_PAYLOAD = {
    "renda_mensal": 4200,
    "objetivo": "juntar para viagem",
    "tolerancia_risco": "baixa",
    "preferencias": "nao quero investimento agressivo",
}

_REGISTRO = {**_PAYLOAD, "renda_mensal": 4200.0}


def _autenticar_como(user_id: str):
    app.dependency_overrides[get_current_user] = lambda: user_id


def _async(valor):
    async def _fn(*_args, **_kwargs):
        return valor

    return _fn


def test_renda_mensal_negativa_e_recusada(client):
    _autenticar_como("user-1")

    assert client.put("/v1/perfil", json={**_PAYLOAD, "renda_mensal": -5}).status_code == 422


def test_renda_mensal_zero_e_recusada(client):
    _autenticar_como("user-1")

    assert client.put("/v1/perfil", json={**_PAYLOAD, "renda_mensal": 0}).status_code == 422


def test_tolerancia_risco_fora_da_lista_e_recusada(client):
    _autenticar_como("user-1")

    assert client.put(
        "/v1/perfil", json={**_PAYLOAD, "tolerancia_risco": "extrema"}
    ).status_code == 422


def test_objetivo_vazio_e_recusado(client):
    _autenticar_como("user-1")

    assert client.put("/v1/perfil", json={**_PAYLOAD, "objetivo": ""}).status_code == 422


def test_objetivo_ausente_e_recusado(client):
    _autenticar_como("user-1")
    payload = {k: v for k, v in _PAYLOAD.items() if k != "objetivo"}

    assert client.put("/v1/perfil", json=payload).status_code == 422


def test_salvar_perfil_devolve_o_perfil_gravado(client, monkeypatch):
    _autenticar_como("user-1")
    monkeypatch.setattr(chat_service, "salvar_perfil_financeiro", _async({"user_id": "user-1", **_REGISTRO}))

    resposta = client.put("/v1/perfil", json=_PAYLOAD)

    assert resposta.status_code == 200
    assert resposta.json() == _REGISTRO


def test_salvar_perfil_pega_user_id_do_token_nao_do_corpo(client, monkeypatch):
    _autenticar_como("user-do-token")
    recebido = {}

    async def _fake(**kwargs):
        recebido.update(kwargs)
        return {"user_id": "user-do-token", **_REGISTRO}

    monkeypatch.setattr(chat_service, "salvar_perfil_financeiro", _fake)

    client.put("/v1/perfil", json={**_PAYLOAD, "user_id": "user-forjado-no-corpo"})

    assert recebido == {
        "user_id": "user-do-token",
        "renda_mensal": 4200.0,
        "objetivo": "juntar para viagem",
        "tolerancia_risco": "baixa",
        "preferencias": "nao quero investimento agressivo",
    }


def test_obter_perfil_inexistente_retorna_404(client, monkeypatch):
    _autenticar_como("user-1")
    monkeypatch.setattr(chat_service, "obter_perfil_financeiro", _async(None))

    assert client.get("/v1/perfil").status_code == 404


def test_obter_perfil_devolve_cadastro(client, monkeypatch):
    _autenticar_como("user-1")
    monkeypatch.setattr(
        chat_service, "obter_perfil_financeiro", _async({"user_id": "user-1", **_REGISTRO})
    )

    resposta = client.get("/v1/perfil")

    assert resposta.status_code == 200
    assert resposta.json() == _REGISTRO

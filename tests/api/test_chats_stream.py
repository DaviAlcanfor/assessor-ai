from assessor_ai.api.app import app
from assessor_ai.api.auth import get_current_principal, get_current_user
from assessor_ai.schemas.auth import AuthMethod, Principal
from assessor_ai.schemas.execution import AnswerReady, RunFinished, RunStarted
from assessor_ai.services import chat_service

HEADERS = {"X-API-Key": "irrelevante-porque-a-dependencia-e-mockada"}


def _async(valor):
    async def _fn(*_args, **_kwargs):
        return valor

    return _fn


def _autenticar_como(user_id: str):
    app.dependency_overrides[get_current_user] = lambda: user_id
    app.dependency_overrides[get_current_principal] = lambda: Principal(
        user_id=user_id, auth_method=AuthMethod.API_KEY
    )


def _stream_fake(*eventos):
    async def _fn(*_args, **_kwargs):
        for evento in eventos:
            yield evento

    return _fn


def test_send_message_stream_retorna_eventos_sse_em_ordem(client, monkeypatch):
    _autenticar_como("user-1")
    monkeypatch.setattr(chat_service, "obter_dono_chat", _async("user-1"))
    monkeypatch.setattr(
        chat_service,
        "send_message_stream",
        _stream_fake(RunStarted(), AnswerReady(content="resposta"), RunFinished()),
    )

    resposta = client.post(
        "/v1/chats/chat-123/messages/stream", json={"content": "oi"}, headers=HEADERS
    )

    assert resposta.status_code == 200
    assert resposta.headers["content-type"].startswith("text/event-stream")

    corpo = resposta.text
    assert "event: run_started" in corpo
    assert "event: answer_ready" in corpo
    assert '"content":"resposta"' in corpo or '"content": "resposta"' in corpo
    assert corpo.index("event: run_started") < corpo.index("event: answer_ready")
    assert corpo.index("event: answer_ready") < corpo.index("event: run_finished")


def test_send_message_stream_chat_de_outro_usuario_nao_inicia_stream(client, monkeypatch):
    _autenticar_como("user-1")
    monkeypatch.setattr(chat_service, "obter_dono_chat", _async("user-2"))

    resposta = client.post(
        "/v1/chats/chat-123/messages/stream", json={"content": "oi"}, headers=HEADERS
    )

    assert resposta.status_code == 403

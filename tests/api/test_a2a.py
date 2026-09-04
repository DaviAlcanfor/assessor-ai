import pytest

from assessor_ai.a2a.agents import interface as a2a_interface
from assessor_ai.services import chat_service

RPC_HEADERS = {"A2A-Version": "1.0"}


def _async(valor):
    """Stub async: `chat_service` virou corrotina, o monkeypatch precisa devolver uma."""

    async def _fn(*_args, **_kwargs):
        return valor

    return _fn



@pytest.fixture(autouse=True)
def _limpar_sessoes():
    a2a_interface._sessoes.clear()
    yield
    a2a_interface._sessoes.clear()


async def _eco(_user_id, _chat_id, content):
    return f"eco: {content}"


def _payload(texto: str, context_id: str | None = None) -> dict:
    message = {"role": "ROLE_USER", "parts": [{"text": texto}], "message_id": "m1"}
    if context_id:
        message["context_id"] = context_id

    return {
        "jsonrpc": "2.0",
        "id": "1",
        "method": "SendMessage",
        "params": {"message": message},
    }


def test_agent_card_expoe_nome_e_skill(client):
    resposta = client.get("/.well-known/agent-card.json")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["name"] == "Assessor AI"
    assert {s["id"] for s in corpo["skills"]} == {"moneysaving", "agenda", "faq"}


def test_send_message_retorna_resposta_do_chat_service(client, monkeypatch):
    monkeypatch.setattr(chat_service, "iniciar_sessao", _async(("user-1", "chat-1")))
    monkeypatch.setattr(
        chat_service, "send_message", _eco
    )

    resposta = client.post("/a2a", json=_payload("oi"), headers=RPC_HEADERS)

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert "error" not in corpo
    assert corpo["result"]["message"]["parts"][0]["text"] == "eco: oi"


def test_send_message_mesmo_context_id_reusa_sessao(client, monkeypatch):
    chamadas = []

    async def _iniciar():
        chamadas.append(1)
        return ("user-1", "chat-1")

    monkeypatch.setattr(chat_service, "iniciar_sessao", _iniciar)
    monkeypatch.setattr(chat_service, "send_message", _async("ok"))

    r1 = client.post("/a2a", json=_payload("primeira"), headers=RPC_HEADERS)
    context_id = r1.json()["result"]["message"]["contextId"]

    r2 = client.post("/a2a", json=_payload("segunda", context_id), headers=RPC_HEADERS)

    assert r1.status_code == r2.status_code == 200
    assert len(chamadas) == 1


def test_send_message_limite_excedido_vira_texto_de_erro(client, monkeypatch):
    monkeypatch.setattr(chat_service, "iniciar_sessao", _async(("user-1", "chat-1")))

    async def _estourou(user_id, chat_id, content):
        raise chat_service.LimiteDeMensagensExcedido("limite atingido")

    monkeypatch.setattr(chat_service, "send_message", _estourou)

    resposta = client.post("/a2a", json=_payload("oi"), headers=RPC_HEADERS)

    assert resposta.status_code == 200
    assert resposta.json()["result"]["message"]["parts"][0]["text"] == "limite atingido"

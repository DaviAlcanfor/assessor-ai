from assessor_ai.api.app import app
from assessor_ai.api.auth import get_current_user
from assessor_ai.schemas.models import ChatMessage
from assessor_ai.schemas.models import Role as DomainRole
from assessor_ai.services import chat_service
from assessor_ai.services.exceptions import FalhaNoAgente, LimiteDeMensagensExcedido

HEADERS = {"X-API-Key": "irrelevante-porque-a-dependencia-e-mockada"}


def _async(valor):
    """Stub async: as funções de `chat_service` viraram corrotinas, então o monkeypatch
    precisa devolver uma corrotina (as rotas dão `await` nelas)."""

    async def _fn(*_args, **_kwargs):
        return valor

    return _fn



def _autenticar_como(user_id: str):
    app.dependency_overrides[get_current_user] = lambda: user_id


def test_create_chat_retorna_chat_id(client, monkeypatch):
    _autenticar_como("user-1")
    monkeypatch.setattr(chat_service, "create_chat", _async("chat-123"))

    resposta = client.post("/v1/chats", headers=HEADERS)

    assert resposta.status_code == 201
    assert resposta.json() == {"chat_id": "chat-123"}


def test_create_chat_erro_interno_vira_500(client_sem_reraise, monkeypatch):
    _autenticar_como("user-1")

    async def _explode(user_id):
        raise RuntimeError("mongo fora do ar")

    monkeypatch.setattr(chat_service, "create_chat", _explode)

    resposta = client_sem_reraise.post("/v1/chats", headers=HEADERS)

    assert resposta.status_code == 500
    # o texto cru da exceção não pode vazar pro cliente
    assert resposta.json() == {"detail": "Erro interno inesperado.", "code": "erro_interno"}
    assert "mongo fora do ar" not in resposta.text


def test_send_message_chat_inexistente_retorna_404(client, monkeypatch):
    _autenticar_como("user-1")
    monkeypatch.setattr(chat_service, "obter_dono_chat", _async(None))

    resposta = client.post(
        "/v1/chats/chat-123/messages", json={"content": "oi"}, headers=HEADERS
    )

    assert resposta.status_code == 404


def test_send_message_chat_de_outro_usuario_retorna_403(client, monkeypatch):
    _autenticar_como("user-1")
    monkeypatch.setattr(chat_service, "obter_dono_chat", _async("user-2"))

    resposta = client.post(
        "/v1/chats/chat-123/messages", json={"content": "oi"}, headers=HEADERS
    )

    assert resposta.status_code == 403


def test_send_message_sucesso(client, monkeypatch):
    _autenticar_como("user-1")
    monkeypatch.setattr(chat_service, "obter_dono_chat", _async("user-1"))
    monkeypatch.setattr(
        chat_service, "send_message", _async("resposta do assessor")
    )

    resposta = client.post(
        "/v1/chats/chat-123/messages", json={"content": "quanto eu gastei?"}, headers=HEADERS
    )

    assert resposta.status_code == 200
    assert resposta.json() == {"chat_id": "chat-123", "content": "resposta do assessor"}


def test_send_message_limite_excedido_retorna_429(client, monkeypatch):
    _autenticar_como("user-1")
    monkeypatch.setattr(chat_service, "obter_dono_chat", _async("user-1"))

    async def _estourou(user_id, chat_id, content):
        raise LimiteDeMensagensExcedido("limite atingido")

    monkeypatch.setattr(chat_service, "send_message", _estourou)

    resposta = client.post(
        "/v1/chats/chat-123/messages", json={"content": "oi"}, headers=HEADERS
    )

    assert resposta.status_code == 429


def test_send_message_erro_interno_retorna_500(client_sem_reraise, monkeypatch):
    _autenticar_como("user-1")
    monkeypatch.setattr(chat_service, "obter_dono_chat", _async("user-1"))

    async def _explode(user_id, chat_id, content):
        raise RuntimeError("llm indisponível")

    monkeypatch.setattr(chat_service, "send_message", _explode)

    resposta = client_sem_reraise.post(
        "/v1/chats/chat-123/messages", json={"content": "oi"}, headers=HEADERS
    )

    assert resposta.status_code == 500
    assert "llm indisponível" not in resposta.text


def test_send_message_falha_no_agente_retorna_502(client, monkeypatch):
    """Falha do grafo é caso esperado: vira 502, não 500 genérico."""

    _autenticar_como("user-1")
    monkeypatch.setattr(chat_service, "obter_dono_chat", _async("user-1"))

    async def _explode(user_id, chat_id, content):
        raise FalhaNoAgente("Não foi possível processar a mensagem.")

    monkeypatch.setattr(chat_service, "send_message", _explode)

    resposta = client.post(
        "/v1/chats/chat-123/messages", json={"content": "oi"}, headers=HEADERS
    )

    assert resposta.status_code == 502
    assert resposta.json()["code"] == "falha_no_agente"


def test_send_message_conteudo_vazio_e_rejeitado_pelo_schema(client, monkeypatch):
    _autenticar_como("user-1")
    monkeypatch.setattr(chat_service, "obter_dono_chat", _async("user-1"))

    resposta = client.post(
        "/v1/chats/chat-123/messages", json={"content": ""}, headers=HEADERS
    )

    assert resposta.status_code == 422


def test_get_messages_chat_inexistente_retorna_404(client, monkeypatch):
    _autenticar_como("user-1")
    monkeypatch.setattr(chat_service, "obter_dono_chat", _async(None))

    resposta = client.get("/v1/chats/chat-123/messages", headers=HEADERS)

    assert resposta.status_code == 404


def test_get_messages_chat_de_outro_usuario_retorna_403(client, monkeypatch):
    _autenticar_como("user-1")
    monkeypatch.setattr(chat_service, "obter_dono_chat", _async("user-2"))

    resposta = client.get("/v1/chats/chat-123/messages", headers=HEADERS)

    assert resposta.status_code == 403


def test_get_messages_retorna_historico_convertido(client, monkeypatch):
    _autenticar_como("user-1")
    monkeypatch.setattr(chat_service, "obter_dono_chat", _async("user-1"))
    monkeypatch.setattr(
        chat_service,
        "get_history",
        _async([
            ChatMessage(role=DomainRole.HUMAN, content="quanto eu gastei?"),
            ChatMessage(role=DomainRole.AI, content="R$ 500 esse mês."),
        ]),
    )

    resposta = client.get("/v1/chats/chat-123/messages", headers=HEADERS)

    assert resposta.status_code == 200
    assert resposta.json() == [
        {"role": "user", "content": "quanto eu gastei?"},
        {"role": "assistant", "content": "R$ 500 esse mês."},
    ]


def test_get_messages_sem_historico_retorna_lista_vazia(client, monkeypatch):
    _autenticar_como("user-1")
    monkeypatch.setattr(chat_service, "obter_dono_chat", _async("user-1"))
    monkeypatch.setattr(chat_service, "get_history", _async(None))

    resposta = client.get("/v1/chats/chat-123/messages", headers=HEADERS)

    assert resposta.status_code == 200
    assert resposta.json() == []


def test_list_chats_deriva_titulo_da_primeira_mensagem_humana(client, monkeypatch):
    _autenticar_como("user-1")
    monkeypatch.setattr(
        chat_service,
        "listar_chats",
        _async([
            {
                "session_id": "chat-1",
                "updated_at": "2026-08-25T12:00:00+00:00",
                "messages": [{"role": "human", "content": "quanto eu gastei esse mês?"}],
            }
        ]),
    )

    resposta = client.get("/v1/chats", headers=HEADERS)

    assert resposta.status_code == 200
    assert resposta.json() == [
        {
            "chat_id": "chat-1",
            "title": "quanto eu gastei esse mês?",
            "updated_at": "2026-08-25T12:00:00Z",
        }
    ]


def test_list_chats_trunca_titulo_longo(client, monkeypatch):
    _autenticar_como("user-1")
    texto = "a" * 60
    monkeypatch.setattr(
        chat_service,
        "listar_chats",
        _async([
            {
                "session_id": "chat-1",
                "updated_at": "2026-08-25T12:00:00+00:00",
                "messages": [{"role": "human", "content": texto}],
            }
        ]),
    )

    resposta = client.get("/v1/chats", headers=HEADERS)

    assert resposta.json()[0]["title"] == texto[:40] + "…"


def test_list_chats_sem_mensagens_vira_nova_conversa(client, monkeypatch):
    _autenticar_como("user-1")
    monkeypatch.setattr(
        chat_service,
        "listar_chats",
        _async([
            {"session_id": "chat-1", "updated_at": "2026-08-25T12:00:00+00:00", "messages": []}
        ]),
    )

    resposta = client.get("/v1/chats", headers=HEADERS)

    assert resposta.json()[0]["title"] == "Nova conversa"


def test_list_chats_vazio(client, monkeypatch):
    _autenticar_como("user-1")
    monkeypatch.setattr(chat_service, "listar_chats", _async([]))

    resposta = client.get("/v1/chats", headers=HEADERS)

    assert resposta.status_code == 200
    assert resposta.json() == []

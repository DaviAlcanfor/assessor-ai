from assessor_ai.tools.redis import chat
from assessor_ai.tools.redis.schemas import CHAT_TTL_TIME, N_MESSAGES_ACCEPTED
from tests.tools.redis.fakes import FakeRedis


def test_can_send_message_permite_dentro_do_limite(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(chat, "get_client", lambda: fake)

    for _ in range(N_MESSAGES_ACCEPTED):
        assert chat.can_send_message("user-1") is True


def test_can_send_message_bloqueia_apos_estourar_limite(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(chat, "get_client", lambda: fake)

    for _ in range(N_MESSAGES_ACCEPTED):
        chat.can_send_message("user-1")

    assert chat.can_send_message("user-1") is False


def test_can_send_message_seta_ttl_apenas_na_primeira_mensagem(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(chat, "get_client", lambda: fake)

    chat.can_send_message("user-1")
    assert fake.ttls["chat:user-1:message"] == CHAT_TTL_TIME

    fake.ttls.clear()
    chat.can_send_message("user-1")
    assert "chat:user-1:message" not in fake.ttls


def test_can_send_message_conta_por_usuario_isoladamente(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(chat, "get_client", lambda: fake)

    for _ in range(N_MESSAGES_ACCEPTED):
        chat.can_send_message("user-1")

    assert chat.can_send_message("user-2") is True

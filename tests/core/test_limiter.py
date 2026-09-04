from assessor_ai.core import limiter
from assessor_ai.core.limiter import CHAT_TTL_TIME, N_MESSAGES_ACCEPTED, _chave_mensagem
from tests.fakes import ConnFake, FakeRedis


def test_can_send_message_permite_dentro_do_limite(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(limiter, "redis", ConnFake(fake))

    for _ in range(N_MESSAGES_ACCEPTED):
        assert limiter.can_send_message("user-1") is True


def test_can_send_message_bloqueia_apos_estourar_limite(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(limiter, "redis", ConnFake(fake))

    for _ in range(N_MESSAGES_ACCEPTED):
        limiter.can_send_message("user-1")

    assert limiter.can_send_message("user-1") is False


def test_can_send_message_seta_ttl_apenas_na_primeira_mensagem(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(limiter, "redis", ConnFake(fake))

    limiter.can_send_message("user-1")
    assert fake.ttls["chat:user-1:message"] == CHAT_TTL_TIME

    fake.ttls.clear()
    limiter.can_send_message("user-1")
    assert "chat:user-1:message" not in fake.ttls


def test_can_send_message_conta_por_usuario_isoladamente(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(limiter, "redis", ConnFake(fake))

    for _ in range(N_MESSAGES_ACCEPTED):
        limiter.can_send_message("user-1")

    assert limiter.can_send_message("user-2") is True


def test_chave_mensagem():
    assert _chave_mensagem("user-1") == "chat:user-1:message"

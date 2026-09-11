from assessor_ai.api import session_store
from assessor_ai.config import settings
from tests.fakes import ConnFake, FakeRedis


def test_criar_e_buscar_sessao_ida_e_volta(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(session_store, "redis", ConnFake(fake))

    session_token, csrf_token = session_store.criar_sessao("user-1")
    record = session_store.buscar_sessao(session_token)

    assert record is not None
    assert record.user_id == "user-1"
    assert record.csrf_hash == session_store.hash_csrf(csrf_token)


def test_buscar_sessao_inexistente_retorna_none(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(session_store, "redis", ConnFake(fake))

    assert session_store.buscar_sessao("token-que-nunca-existiu") is None


def test_revogar_sessao_apaga_do_redis(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(session_store, "redis", ConnFake(fake))

    session_token, _ = session_store.criar_sessao("user-1")
    session_store.revogar_sessao(session_token)

    assert session_store.buscar_sessao(session_token) is None


def test_sessao_grava_com_ttl(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(session_store, "redis", ConnFake(fake))

    session_store.criar_sessao("user-1")
    chave = next(iter(fake.ttls))

    assert fake.ttls[chave] == settings.SESSION_TTL_SECONDS

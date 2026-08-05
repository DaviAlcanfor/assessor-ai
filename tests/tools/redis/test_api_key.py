from assessor_ai.tools.redis import api_key
from assessor_ai.tools.redis.schemas import API_KEY_TTL_TIME, _hash_api_key
from tests.tools.redis.fakes import FakeRedis


def test_allocate_api_key_grava_hash_e_lookup(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(api_key, "get_client", lambda: fake)

    assert api_key.allocate_api_key("user-1", "minha-chave") is True

    hashed = _hash_api_key("minha-chave")
    assert fake.store["auth:user:user-1:api-key-hash"] == hashed
    assert fake.store["auth:api-key:" + hashed] == "user-1"
    assert fake.ttls["auth:user:user-1:api-key-hash"] == API_KEY_TTL_TIME
    assert fake.ttls["auth:api-key:" + hashed] == API_KEY_TTL_TIME


def test_allocate_api_key_recusa_se_usuario_ja_tem_chave(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(api_key, "get_client", lambda: fake)

    api_key.allocate_api_key("user-1", "primeira-chave")

    assert api_key.allocate_api_key("user-1", "segunda-chave") is False
    assert fake.store["auth:user:user-1:api-key-hash"] == _hash_api_key("primeira-chave")


def test_get_user_id_by_api_key_encontra_usuario(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(api_key, "get_client", lambda: fake)

    api_key.allocate_api_key("user-1", "minha-chave")

    assert api_key.get_user_id_by_api_key("minha-chave") == "user-1"


def test_get_user_id_by_api_key_retorna_none_para_chave_invalida(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(api_key, "get_client", lambda: fake)

    assert api_key.get_user_id_by_api_key("chave-que-nao-existe") is None

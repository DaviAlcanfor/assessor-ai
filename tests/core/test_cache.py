from assessor_ai.core import cache
from assessor_ai.core.cache import PROFILE_TTL_TIME, _chave_perfil
from tests.fakes import ConnFake, FakeRedis


def test_buscar_perfil_cache_retorna_none_quando_nao_existe(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(cache, "redis", ConnFake(fake))

    assert cache.buscar_perfil_cache("user-1") is None


def test_salvar_e_buscar_perfil_cache(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(cache, "redis", ConnFake(fake))

    cache.salvar_perfil_cache("user-1", "gasta muito com delivery")

    assert cache.buscar_perfil_cache("user-1") == "gasta muito com delivery"
    assert fake.ttls["user:user-1:profile"] == PROFILE_TTL_TIME


def test_invalidar_perfil_cache_remove_a_chave(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(cache, "redis", ConnFake(fake))

    cache.salvar_perfil_cache("user-1", "perfil qualquer")
    cache.invalidar_perfil_cache("user-1")

    assert cache.buscar_perfil_cache("user-1") is None


def test_invalidar_perfil_cache_sem_cache_existente_nao_quebra(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(cache, "redis", ConnFake(fake))

    cache.invalidar_perfil_cache("user-inexistente")


def test_chave_perfil():
    assert _chave_perfil("user-1") == "user:user-1:profile"

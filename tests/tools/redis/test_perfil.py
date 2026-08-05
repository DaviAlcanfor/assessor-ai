from assessor_ai.tools.redis import perfil
from assessor_ai.tools.redis.schemas import PROFILE_TTL_TIME
from tests.tools.redis.fakes import FakeRedis


def test_buscar_perfil_cache_retorna_none_quando_nao_existe(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(perfil, "get_client", lambda: fake)

    assert perfil.buscar_perfil_cache("user-1") is None


def test_salvar_e_buscar_perfil_cache(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(perfil, "get_client", lambda: fake)

    perfil.salvar_perfil_cache("user-1", "gasta muito com delivery")

    assert perfil.buscar_perfil_cache("user-1") == "gasta muito com delivery"
    assert fake.ttls["user:user-1:profile"] == PROFILE_TTL_TIME


def test_invalidar_perfil_cache_remove_a_chave(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(perfil, "get_client", lambda: fake)

    perfil.salvar_perfil_cache("user-1", "perfil qualquer")
    perfil.invalidar_perfil_cache("user-1")

    assert perfil.buscar_perfil_cache("user-1") is None


def test_invalidar_perfil_cache_sem_cache_existente_nao_quebra(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(perfil, "get_client", lambda: fake)

    perfil.invalidar_perfil_cache("user-inexistente")

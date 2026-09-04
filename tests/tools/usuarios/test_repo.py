from assessor_ai.graph.tools.usuarios.repo import UsuariosRepo
from assessor_ai.graph.tools.usuarios.schemas import API_KEY_TTL_TIME, hash_api_key
from tests.fakes import FakeRedis


class _CacheFake:
    def __init__(self, fake):
        self.client = fake


def test_allocate_api_key_grava_hash_e_lookup(monkeypatch):
    fake = FakeRedis()
    repo = UsuariosRepo(cache=_CacheFake(fake))

    assert repo.alocar_api_key("user-1", "minha-chave") is True

    hashed = hash_api_key("minha-chave")
    assert fake.store["auth:user:user-1:api-key-hash"] == hashed
    assert fake.store["auth:api-key:" + hashed] == "user-1"
    assert fake.ttls["auth:user:user-1:api-key-hash"] == API_KEY_TTL_TIME
    assert fake.ttls["auth:api-key:" + hashed] == API_KEY_TTL_TIME


def test_allocate_api_key_recusa_se_usuario_ja_tem_chave(monkeypatch):
    fake = FakeRedis()
    repo = UsuariosRepo(cache=_CacheFake(fake))

    repo.alocar_api_key("user-1", "primeira-chave")

    assert repo.alocar_api_key("user-1", "segunda-chave") is False
    assert fake.store["auth:user:user-1:api-key-hash"] == hash_api_key("primeira-chave")


def test_get_user_id_by_api_key_encontra_usuario(monkeypatch):
    fake = FakeRedis()
    repo = UsuariosRepo(cache=_CacheFake(fake))

    repo.alocar_api_key("user-1", "minha-chave")

    assert repo.user_id_por_api_key("minha-chave") == "user-1"


def test_get_user_id_by_api_key_retorna_none_para_chave_invalida(monkeypatch):
    fake = FakeRedis()
    repo = UsuariosRepo(cache=_CacheFake(fake))

    assert repo.user_id_por_api_key("chave-que-nao-existe") is None

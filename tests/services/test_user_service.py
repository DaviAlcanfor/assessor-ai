from app.repositories.usuario_repository import usuario_repository
from app.services import user_service


async def test_obter_usuario_padrao_reaproveita_usuario_existente(monkeypatch):
    monkeypatch.setattr(usuario_repository, "buscar_algum", lambda: {"user_id": "user-existente"})

    assert await user_service.obter_usuario_padrao() == "user-existente"


async def test_obter_usuario_padrao_cria_usuario_mock_quando_nao_ha_nenhum(monkeypatch):
    monkeypatch.setattr(usuario_repository, "buscar_algum", lambda: None)

    criado = {}

    def _garantir(user_id, nome, email):
        criado.update(user_id=user_id, nome=nome, email=email)

    monkeypatch.setattr(usuario_repository, "garantir_usuario", _garantir)

    user_id = await user_service.obter_usuario_padrao()

    assert user_id == criado["user_id"]
    assert criado["nome"] and criado["email"]


async def test_obter_ou_criar_usuario_devolve_o_existente_por_email(monkeypatch):
    monkeypatch.setattr(usuario_repository, "buscar_por_email", lambda email: {"user_id": "user-1"})

    assert await user_service.obter_ou_criar_usuario("Ana", "ana@exemplo.com") == "user-1"


async def test_buscar_perfil_usa_o_cache_e_nao_vai_ao_mongo(monkeypatch):
    monkeypatch.setattr(user_service, "buscar_perfil_cache", lambda user_id: "perfil-em-cache")

    def _nao_deveria_chamar(user_id):
        raise AssertionError("foi ao Mongo com o perfil em cache")

    monkeypatch.setattr(usuario_repository, "buscar", _nao_deveria_chamar)

    assert await user_service.buscar_perfil("user-1") == "perfil-em-cache"

"""Resolução do `category_name` livre do LLM: igualdade exata → JeV escolhe entre as categorias reais →
sem categoria (com `aviso`). O gateway está desligado por padrão nos testes (tests/conftest.py)."""

from datetime import UTC, datetime

import pytest

from app.infra.postgres.models import Category, Transaction
from app.services import financeiro_service as servico


@pytest.fixture
def categorias(db_session):
    for nome, descricao in [("Mercado", "compras de supermercado e feira"), ("Transporte", "uber, ônibus, gasolina")]:
        db_session.add(Category(name=nome, description=descricao, created_at=datetime.now(UTC)))
    db_session.commit()


@pytest.fixture(autouse=True)
def cache(monkeypatch):
    """Redis em memória (nunca o real): `escolhas` é o que o cache guardou, por chave."""

    escolhas: dict[str, str] = {}
    monkeypatch.setattr(servico, "buscar_categoria_cache", escolhas.get)
    monkeypatch.setattr(servico, "salvar_categoria_cache", escolhas.__setitem__)
    return escolhas


@pytest.fixture
def jev(monkeypatch):
    """JeV ligado, com a escolha controlada pelo teste; guarda o que foi perguntado."""

    estado = {"escolha": "Mercado", "perguntas": [], "erro": None}

    async def escolher(uso, entrada, instrucoes, opcoes):
        estado["perguntas"].append({"uso": uso, "entrada": entrada, "opcoes": list(opcoes)})
        if estado["erro"]:
            raise estado["erro"]
        return estado["escolha"]

    monkeypatch.setattr(servico.jev, "disponivel", lambda: True)
    monkeypatch.setattr(servico.jev, "escolher", escolher)
    return estado


async def test_nome_exato_nao_chama_o_jev(financeiro, categorias, jev):
    resposta = await financeiro.add_transaction(amount=10, source_text="feira", category_name="mercado")

    assert resposta["category"] == "Mercado"
    assert "aviso" not in resposta
    assert jev["perguntas"] == []


async def test_nome_que_nao_bate_e_resolvido_pelo_jev_entre_as_categorias_reais(
    financeiro, categorias, jev, db_session
):
    resposta = await financeiro.add_transaction(
        amount=42.5, source_text="gastei 42,50 no supermercado", category_name="supermercado"
    )

    assert resposta["status"] == "ok"
    assert resposta["category"] == "Mercado"
    assert "aviso" not in resposta
    [pergunta] = jev["perguntas"]
    assert pergunta["uso"] == "categoria_transacao"
    assert set(pergunta["opcoes"]) == {"Mercado", "Transporte", "nenhuma"}
    assert "supermercado" in pergunta["entrada"]
    assert db_session.get(Transaction, resposta["id"]).category.name == "Mercado"


async def test_jev_diz_nenhuma_grava_sem_categoria_e_avisa(financeiro, categorias, jev, db_session):
    jev["escolha"] = "nenhuma"

    resposta = await financeiro.add_transaction(amount=5, source_text="presente", category_name="presentes")

    assert resposta["status"] == "ok"  # o lançamento não se perde
    assert resposta["category"] is None
    assert "sem categoria" in resposta["aviso"]
    assert db_session.get(Transaction, resposta["id"]).category_id is None


async def test_jev_inventando_categoria_fora_da_lista_vira_sem_categoria(financeiro, categorias, jev):
    jev["escolha"] = "Lazer"  # não existe: o service só aceita nome que está na tabela

    resposta = await financeiro.add_transaction(amount=5, source_text="cinema", category_name="cinema")

    assert resposta["category"] is None
    assert "aviso" in resposta


async def test_jev_com_falha_nao_derruba_o_lancamento(financeiro, categorias, jev):
    jev["erro"] = RuntimeError("403 customer_verification_required")

    resposta = await financeiro.add_transaction(amount=5, source_text="uber", category_name="corrida")

    assert resposta["status"] == "ok"
    assert resposta["category"] is None
    assert "aviso" in resposta


async def test_sem_gateway_nome_que_nao_bate_fica_sem_categoria_e_avisa(financeiro, categorias):
    resposta = await financeiro.add_transaction(amount=5, source_text="uber", category_name="corrida")

    assert resposta["status"] == "ok"
    assert resposta["category"] is None
    assert "corrida" in resposta["aviso"]


async def test_sem_category_name_nao_aviso_e_nao_chama_o_jev(financeiro, categorias, jev):
    resposta = await financeiro.add_transaction(amount=5, source_text="algo")

    assert resposta["category"] is None
    assert "aviso" not in resposta
    assert jev["perguntas"] == []


async def test_update_resolve_a_categoria_pelo_jev(financeiro, categorias, jev, db_session):
    criada = await financeiro.add_transaction(amount=30, source_text="corrida de app")
    jev["escolha"] = "Transporte"

    resposta = await financeiro.update_transaction(id=criada["id"], category_name="uber")

    assert resposta["updated"]["category"] == "Transporte"


async def test_update_com_categoria_irresolvivel_nao_altera_nada_e_explica(financeiro, categorias, jev, db_session):
    criada = await financeiro.add_transaction(amount=30, source_text="algo", category_name="mercado")
    jev["escolha"] = "nenhuma"

    resposta = await financeiro.update_transaction(id=criada["id"], category_name="xyz", amount=999)

    assert resposta["status"] == "error"
    assert "nada foi alterado" in resposta["message"]
    assert float(db_session.get(Transaction, criada["id"]).amount) == 30.0


async def test_escolha_do_jev_vai_pro_cache_e_a_segunda_vez_nao_pergunta(financeiro, categorias, jev, cache):
    await financeiro.add_transaction(amount=1, source_text="a", category_name="supermercado")
    await financeiro.add_transaction(amount=2, source_text="b", category_name="Supermercado ")  # mesmo nome normalizado

    assert len(jev["perguntas"]) == 1
    assert list(cache.values()) == ["Mercado"]


async def test_nenhuma_tambem_e_cacheada(financeiro, categorias, jev, cache):
    jev["escolha"] = "nenhuma"

    await financeiro.add_transaction(amount=1, source_text="a", category_name="presentes")
    resposta = await financeiro.add_transaction(amount=2, source_text="b", category_name="presentes")

    assert len(jev["perguntas"]) == 1
    assert resposta["category"] is None and "aviso" in resposta


async def test_falha_do_jev_nao_vai_pro_cache(financeiro, categorias, jev, cache):
    jev["erro"] = RuntimeError("403")

    await financeiro.add_transaction(amount=1, source_text="a", category_name="corrida")

    assert cache == {}


async def test_nova_categoria_invalida_o_cache_porque_a_chave_muda(financeiro, categorias, jev, cache, db_session):
    await financeiro.add_transaction(amount=1, source_text="a", category_name="supermercado")
    db_session.add(Category(name="Lazer", description="cinema, bar", created_at=datetime.now(UTC)))
    db_session.commit()

    await financeiro.add_transaction(amount=2, source_text="b", category_name="supermercado")

    assert len(jev["perguntas"]) == 2  # o conjunto de categorias mudou: pergunta de novo
    assert len(cache) == 2


async def test_redis_fora_do_ar_e_so_cache_miss_e_o_lancamento_funciona(financeiro, categorias, jev, monkeypatch):
    def quebrado(*_args):
        raise ConnectionError("redis fora")

    monkeypatch.setattr(servico, "buscar_categoria_cache", quebrado)
    monkeypatch.setattr(servico, "salvar_categoria_cache", quebrado)

    resposta = await financeiro.add_transaction(amount=1, source_text="a", category_name="supermercado")

    assert resposta["status"] == "ok"
    assert resposta["category"] == "Mercado"

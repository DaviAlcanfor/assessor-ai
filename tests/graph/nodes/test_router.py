from langchain_core.messages import AIMessage, HumanMessage

from app.graph.nodes.router import (
    _extrair_pergunta,
    _extrair_rota,
    no_roteador,
)
from app.graph.state import Route


def test_extrair_rota_reconhece_rota_valida():
    assert _extrair_rota("ROUTE=financeiro") == Route.FINANCEIRO


def test_extrair_rota_sem_match_retorna_fim():
    assert _extrair_rota("resposta sem o padrão esperado") == Route.FIM


def test_extrair_rota_valor_desconhecido_retorna_fim():
    assert _extrair_rota("ROUTE=inexistente") == Route.FIM


def test_extrair_pergunta_captura_o_resto_da_linha():
    texto = "ROUTE=financeiro\nPERGUNTA_ORIGINAL=quanto eu gastei esse mês?"

    assert _extrair_pergunta(texto) == "quanto eu gastei esse mês?"


def test_extrair_pergunta_sem_match_retorna_string_vazia():
    assert _extrair_pergunta("ROUTE=FIM") == ""


def _estado(*textos: str) -> dict:
    return {"messages": [HumanMessage(content=t) for t in textos]}


async def test_roteador_com_jev_usa_a_rota_escolhida_e_a_ultima_mensagem(monkeypatch):
    async def _escolher(uso, entrada, instrucoes, opcoes):
        assert entrada == "marca dentista amanhã às 10h"
        return "agenda"

    async def _llm_nao_deve_rodar(*_args):
        raise AssertionError("LLM não deveria ser chamado")

    monkeypatch.setattr("app.infra.llm.jev.disponivel", lambda: True)
    monkeypatch.setattr("app.infra.llm.jev.escolher", _escolher)
    monkeypatch.setattr("app.graph.nodes.router.responder", _llm_nao_deve_rodar)

    update = await no_roteador(_estado("oi", "marca dentista amanhã às 10h"))

    assert update["rota"] == Route.AGENDA
    assert update["pergunta_original"] == "marca dentista amanhã às 10h"
    assert "messages" not in update


async def test_roteador_com_jev_nenhum_devolve_a_vez_pro_llm(monkeypatch):
    async def _escolher(*_args):
        return "nenhum"

    async def _responder(*_args):
        return "Olá! Posso ajudar com finanças ou agenda."

    monkeypatch.setattr("app.infra.llm.jev.disponivel", lambda: True)
    monkeypatch.setattr("app.infra.llm.jev.escolher", _escolher)
    monkeypatch.setattr("app.graph.nodes.router.responder", _responder)

    update = await no_roteador(_estado("oi"))

    assert update["rota"] == Route.FIM
    assert isinstance(update["messages"][0], AIMessage)

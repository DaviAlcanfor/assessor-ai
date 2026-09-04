from assessor_ai.graph.agents.nodes.router import _extrair_pergunta, _extrair_rota
from assessor_ai.graph.state import Route


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

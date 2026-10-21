"""MercadoTools: a tool só embrulha o service em `Response` — erro de domínio vira mensagem pública,
qualquer outra coisa vira texto genérico (e não vaza detalhe pro LLM)."""

from app.domain.errors import DadosInvalidos
from app.graph.tools.mercado.tools import MercadoTools
from app.infra.mercado import MercadoError


class _ServicoFalso:
    async def converter_moeda(self, valor, de, para):
        return {"valor_convertido": valor * 5.0}

    async def cotacao_atual(self, moedas):
        raise DadosInvalidos("Código de moeda inválido: 'X'.")

    async def ptax_dolar(self, data_inicio, data_fim=None):
        raise MercadoError("O serviço de cotações (bcb) está indisponível agora.")

    async def indicador_economico(self, indicador, ultimos=1):
        raise RuntimeError("psycopg2.OperationalError: connection string postgresql://u:senha@host")


def _tools() -> MercadoTools:
    return MercadoTools(_ServicoFalso())  # type: ignore[arg-type]


async def test_sucesso_vira_response_ok_com_o_payload_do_service():
    resposta = await _tools().converter_moeda(100, "USD", "BRL")

    assert resposta == {"status": "ok", "valor_convertido": 500.0}


async def test_erro_de_entrada_vira_response_error_com_a_mensagem_do_service():
    resposta = await _tools().cotacao_atual(["X"])

    assert resposta == {"status": "error", "message": "Código de moeda inválido: 'X'."}


async def test_api_fora_do_ar_vira_response_error_com_mensagem_segura():
    resposta = await _tools().ptax_dolar("2026-10-16")

    assert resposta == {"status": "error", "message": "O serviço de cotações (bcb) está indisponível agora."}


async def test_excecao_inesperada_nao_vaza_detalhe_pro_llm():
    resposta = await _tools().indicador_economico("selic")

    assert resposta["status"] == "error"
    assert "senha" not in resposta["message"]
    assert "postgresql" not in resposta["message"]


def test_as_tools_expoe_as_seis_tools_com_nomes_estaveis_e_schema():
    tools = {t.name: t for t in _tools().as_tools()}

    assert set(tools) == {
        "cotacao_atual", "cotacao_historica", "ptax_dolar",
        "converter_moeda", "indicador_economico", "simular_investimento",
    }
    assert "moedas" in tools["cotacao_atual"].args  # vem do args_schema
    assert "Cotação atual" in tools["cotacao_atual"].description  # vem da docstring

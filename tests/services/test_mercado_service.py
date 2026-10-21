"""MercadoService com a camada HTTP (infra.mercado) substituída: parse, cálculo e erros."""

import pytest

from app.domain.errors import DadosInvalidos
from app.infra.mercado import MercadoError
from app.infra.mercado.schemas import CotacaoAtual, CotacaoDia, PontoSerie, PtaxDia
from app.services import mercado_service as servico
from app.services.mercado_service import MercadoService


def _atual(code: str, bid: float, ask: float | None = None) -> CotacaoAtual:
    return CotacaoAtual(
        code=code, codein="BRL", name=f"{code}/BRL", bid=bid, ask=ask or bid + 0.01,
        high=bid + 1, low=bid - 1, pctChange=0.5, create_date="2026-10-21 10:00:00",
    )


@pytest.fixture
def mercado(monkeypatch):
    """Cotações atuais fixas: dólar 5, euro 6, bitcoin 300 mil."""

    tabela = {"USD": _atual("USD", 5.0), "EUR": _atual("EUR", 6.0), "BTC": _atual("BTC", 300_000.0)}

    async def cotacoes_atuais(pares):
        return {p.replace("-", ""): tabela[p.split("-")[0]] for p in pares}

    monkeypatch.setattr(servico.awesomeapi, "cotacoes_atuais", cotacoes_atuais)
    return MercadoService()


async def test_cotacao_atual_devolve_campos_em_portugues_e_nao_repete_moeda(mercado):
    cotacoes = await mercado.cotacao_atual(["usd", "USD", "eur"])

    assert [c["moeda"] for c in cotacoes] == ["USD", "EUR"]
    assert cotacoes[0]["compra"] == 5.0
    assert cotacoes[0]["atualizado_em"] == "2026-10-21 10:00:00"


@pytest.mark.parametrize("codigo", ["", "U", "US1", "DOLAR!!", "123"])
async def test_cotacao_atual_recusa_codigo_invalido(mercado, codigo):
    with pytest.raises(DadosInvalidos):
        await mercado.cotacao_atual([codigo])


@pytest.mark.parametrize(
    ("valor", "de", "para", "esperado"),
    [
        (200, "USD", "BRL", 1000.0),
        (1000, "BRL", "USD", 200.0),
        (100, "USD", "EUR", 83.33),  # cruza pelo real: 5 / 6
        (50, "BRL", "BRL", 50.0),
    ],
)
async def test_converter_moeda_passa_pelo_real(mercado, valor, de, para, esperado):
    conversao = await mercado.converter_moeda(valor, de, para)

    assert conversao["valor_convertido"] == esperado


def _dias(n: int) -> list[CotacaoDia]:
    # timestamp de 2026-10-01 12:00 em diante, um por dia, cotação subindo 0,01 por dia; a API devolve do mais novo ao mais antigo
    base = 1790856000
    dias = [
        CotacaoDia(bid=5 + i / 100, ask=5.01 + i / 100, high=6, low=4, timestamp=base + i * 86400)
        for i in range(n)
    ]
    return list(reversed(dias))


async def test_cotacao_historica_resume_e_ordena_do_mais_antigo(monkeypatch):
    async def diarias(par, inicio, fim):
        assert par == "USD-BRL"
        return _dias(5)

    monkeypatch.setattr(servico.awesomeapi, "cotacoes_diarias", diarias)

    historico = await MercadoService().cotacao_historica("usd", "2026-10-01", "2026-10-05")

    assert historico["resumo"]["primeira"] == 5.0
    assert historico["resumo"]["ultima"] == 5.04
    assert historico["resumo"]["variacao_pct"] == 0.8
    assert [p["cotacao"] for p in historico["pontos"]] == [5.0, 5.01, 5.02, 5.03, 5.04]


async def test_cotacao_historica_longa_e_amostrada_mantendo_pontas(monkeypatch):
    async def diarias(*_args):
        return _dias(200)

    monkeypatch.setattr(servico.awesomeapi, "cotacoes_diarias", diarias)

    historico = await MercadoService().cotacao_historica("USD", "2026-01-01", "2026-07-19")

    assert len(historico["pontos"]) == 31
    assert historico["pontos"][0]["cotacao"] == 5.0
    assert historico["pontos"][-1]["cotacao"] == 6.99
    assert historico["resumo"]["dias_com_cotacao"] == 200


@pytest.mark.parametrize(
    ("inicio", "fim"),
    [("01/10/2026", "05/10/2026"), ("2026-10-05", "2026-10-01"), ("2024-01-01", "2026-01-01")],
)
async def test_cotacao_historica_recusa_datas_ruins(mercado, inicio, fim):
    with pytest.raises(DadosInvalidos):
        await MercadoService().cotacao_historica("USD", inicio, fim)


async def test_ptax_em_dia_sem_boletim_devolve_o_ultimo_fechamento_anterior(monkeypatch):
    sexta = PtaxDia(cotacaoCompra=5.08, cotacaoVenda=5.0826, dataHoraCotacao="2026-10-16 13:04:14.548156")
    chamadas = []

    async def ptax_fake(inicio, fim):
        chamadas.append((inicio, fim))
        return [] if len(chamadas) == 1 else [sexta]  # domingo vazio; a janela de 7 dias acha a sexta

    monkeypatch.setattr(servico.ptax, "dolar", ptax_fake)

    resultado = await MercadoService().ptax_dolar("2026-10-18")

    assert resultado["ptax"] == [{"data": "2026-10-16", "compra": 5.08, "venda": 5.0826}]
    assert "último fechamento anterior" in resultado["observacao"]


async def test_ptax_de_periodo_sem_nenhum_dia_util_e_erro(monkeypatch):
    async def vazio(*_args):
        return []

    monkeypatch.setattr(servico.ptax, "dolar", vazio)

    with pytest.raises(DadosInvalidos):
        await MercadoService().ptax_dolar("2026-10-17", "2026-10-18")


@pytest.mark.parametrize(
    ("indicador", "codigo", "ultimos", "dias_da_janela"),
    [
        ("selic", 432, 1, 45),           # diária: janela fixa
        ("cdi", 4389, 1, 45),
        ("ipca", 433, 3, 31 * (3 + 2)),  # mensal: 1 ponto por mês + folga pro mês que ainda não saiu
        ("ipca_12m", 13522, 1, 31 * (1 + 2)),
    ],
)
async def test_indicador_pede_ao_bcb_uma_janela_que_termina_hoje(monkeypatch, indicador, codigo, ultimos, dias_da_janela):
    hoje = servico.date(2026, 10, 21)
    monkeypatch.setattr(servico, "_hoje", lambda: hoje)
    pedidos = []

    async def serie(cod, inicio, fim):
        pedidos.append((cod, inicio, fim))
        return [PontoSerie(data=f"{d:02d}/09/2026", valor=float(d)) for d in range(1, 6)]

    monkeypatch.setattr(servico.sgs, "serie", serie)

    resultado = await MercadoService().indicador_economico(indicador, ultimos)

    assert pedidos == [(codigo, hoje - servico.timedelta(days=dias_da_janela), hoje)]
    assert len(resultado["valores"]) == ultimos
    assert resultado["valores"][-1] == {"data": "2026-09-05", "valor": 5.0}  # o mais recente vem por último


async def test_indicador_sem_nenhum_ponto_na_janela_e_erro(monkeypatch):
    async def vazio(*_args):
        return []

    monkeypatch.setattr(servico.sgs, "serie", vazio)

    with pytest.raises(MercadoError):
        await MercadoService().indicador_economico("ipca")


@pytest.mark.parametrize(
    ("kwargs", "final", "rendimento"),
    [
        ({"valor_inicial": 1000, "meses": 12, "taxa_anual_percentual": 12}, 1120.0, 120.0),
        ({"valor_inicial": 0, "meses": 12, "aporte_mensal": 100, "taxa_anual_percentual": 0}, 1200.0, 0.0),
        ({"valor_inicial": 1000, "meses": 24, "taxa_anual_percentual": 10}, 1210.0, 210.0),
    ],
)
async def test_simulacao_por_taxa_fixa_bate_com_juros_compostos(kwargs, final, rendimento):
    simulacao = await MercadoService().simular_investimento(**kwargs)

    assert simulacao["valor_final_bruto"] == final
    assert simulacao["rendimento_bruto"] == rendimento
    assert "sem garantia" in simulacao["aviso"]


async def test_simulacao_por_percentual_do_cdi_usa_a_taxa_atual(monkeypatch):
    monkeypatch.setattr(servico, "_hoje", lambda: servico.date(2026, 10, 21))

    async def serie(codigo, inicio, fim):
        assert codigo == 4389
        return [PontoSerie(data="20/10/2026", valor=10.0)]

    monkeypatch.setattr(servico.sgs, "serie", serie)

    simulacao = await MercadoService().simular_investimento(
        valor_inicial=1000, meses=12, indicador="cdi", percentual_do_indicador=110
    )

    assert simulacao["taxa_anual_pct"] == 11.0
    assert simulacao["valor_final_bruto"] == 1110.0
    assert simulacao["taxa_usada"].startswith("110% do CDI")


@pytest.mark.parametrize(
    "kwargs",
    [
        {"valor_inicial": 1000, "meses": 12},  # sem taxa nem indicador
        {"valor_inicial": 1000, "meses": 12, "taxa_anual_percentual": 10, "indicador": "cdi"},  # os dois
    ],
)
async def test_simulacao_exige_taxa_ou_indicador(kwargs):
    with pytest.raises(DadosInvalidos):
        await MercadoService().simular_investimento(**kwargs)

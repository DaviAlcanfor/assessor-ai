"""AwesomeAPI e BCB com o HTTP stubado: contrato do pedido, parse, cache e erros."""

from datetime import date

import httpx
import pytest

from assessor_ai.infra.mercado import MercadoError, awesomeapi, bcb
from assessor_ai.infra.mercado import http as mercado_http

_USDBRL = {
    "USDBRL": {
        "code": "USD", "codein": "BRL", "name": "Dólar Americano/Real Brasileiro",
        "high": "5.0281", "low": "5.0238", "varBid": "0.0043", "pctChange": "0.085595",
        "bid": "5.0281", "ask": "5.0285", "timestamp": "1792567908", "create_date": "2026-10-21 04:31:48",
    }
}


@pytest.fixture
def rede(monkeypatch):
    """Responde qualquer GET com `resposta` e guarda as requisições em `pedidos`."""

    pedidos: list[httpx.Request] = []
    estado: dict = {"status": 200, "json": _USDBRL, "texto": None}
    cliente_real = httpx.AsyncClient

    def handler(request: httpx.Request) -> httpx.Response:
        pedidos.append(request)
        if estado["texto"] is not None:
            return httpx.Response(estado["status"], text=estado["texto"])
        return httpx.Response(estado["status"], json=estado["json"])

    monkeypatch.setattr(
        mercado_http.httpx, "AsyncClient",
        lambda **kw: cliente_real(transport=httpx.MockTransport(handler), **kw),
    )
    mercado_http._cache.clear()
    yield pedidos, estado
    mercado_http._cache.clear()


async def test_cotacoes_atuais_converte_strings_e_monta_a_url(rede):
    pedidos, _ = rede

    cotacoes = await awesomeapi.cotacoes_atuais(["USD-BRL", "EUR-BRL"])

    assert str(pedidos[0].url).endswith("/json/last/USD-BRL,EUR-BRL")
    assert cotacoes["USDBRL"].bid == 5.0281
    assert cotacoes["USDBRL"].pct_change == 0.085595
    assert pedidos[0].headers["user-agent"] == "assessor-ai/0.1"


async def test_segunda_chamada_igual_sai_do_cache(rede):
    pedidos, _ = rede

    await awesomeapi.cotacoes_atuais(["USD-BRL"])
    await awesomeapi.cotacoes_atuais(["USD-BRL"])

    assert len(pedidos) == 1


async def test_cache_expira_pelo_ttl(rede, monkeypatch):
    pedidos, _ = rede
    relogio = [1000.0]
    monkeypatch.setattr(mercado_http.time, "monotonic", lambda: relogio[0])

    await awesomeapi.cotacoes_atuais(["USD-BRL"])
    relogio[0] += 61  # ttl_atual_s = 60
    await awesomeapi.cotacoes_atuais(["USD-BRL"])

    assert len(pedidos) == 2


async def test_cotacoes_diarias_manda_periodo_e_numero_de_dias(rede):
    pedidos, estado = rede
    estado["json"] = [{"bid": "5.06", "ask": "5.07", "high": "5.1", "low": "5.0", "timestamp": "1792184463"}]

    dias = await awesomeapi.cotacoes_diarias("USD-BRL", date(2026, 10, 13), date(2026, 10, 17))

    assert "/json/daily/USD-BRL/5" in str(pedidos[0].url)
    assert pedidos[0].url.params["start_date"] == "20261013"
    assert pedidos[0].url.params["end_date"] == "20261017"
    assert dias[0].bid == 5.06


async def test_ptax_manda_datas_no_formato_odata_do_bcb(rede):
    pedidos, estado = rede
    estado["json"] = {"value": [
        {"cotacaoCompra": 5.0, "cotacaoVenda": 5.01, "dataHoraCotacao": "2026-10-13 13:04:26.866133"},
    ]}

    boletins = await bcb.ptax_dolar(date(2026, 10, 13), date(2026, 10, 17))

    params = pedidos[0].url.params
    assert params["@dataInicial"] == "'10-13-2026'"
    assert params["@dataFinalCotacao"] == "'10-17-2026'"
    assert params["$format"] == "json"
    assert boletins[0].venda == 5.01


async def test_ptax_manda_a_query_crua_sem_codificar_o_cifrao(rede):
    """O httpx codificaria `$format` como `%24format` e o OData do BCB responde 400."""

    pedidos, estado = rede
    estado["json"] = {"value": []}

    await bcb.ptax_dolar(date(2026, 10, 13), date(2026, 10, 16))

    query = pedidos[0].url.query.decode()
    assert "$format=json" in query
    assert "%24" not in query
    assert "orderby" not in query


async def test_ptax_ordena_do_mais_antigo_pro_mais_recente(rede):
    _, estado = rede
    estado["json"] = {"value": [
        {"cotacaoCompra": 5.2, "cotacaoVenda": 5.21, "dataHoraCotacao": "2026-10-16 13:00:00.0"},
        {"cotacaoCompra": 5.0, "cotacaoVenda": 5.01, "dataHoraCotacao": "2026-10-13 13:00:00.0"},
    ]}

    boletins = await bcb.ptax_dolar(date(2026, 10, 13), date(2026, 10, 16))

    assert [b.data_hora[:10] for b in boletins] == ["2026-10-13", "2026-10-16"]


async def test_serie_sgs_pede_janela_de_datas_e_ordena_do_mais_antigo(rede):
    """O SGS devolve umas séries em ordem crescente e outras decrescente: a ordem é nossa."""

    pedidos, estado = rede
    estado["json"] = [
        {"data": "19/10/2026", "valor": "13.65"},
        {"data": "16/10/2026", "valor": "13.60"},
    ]

    pontos = await bcb.serie_sgs(4389, date(2026, 9, 1), date(2026, 10, 21))

    params = pedidos[0].url.params
    assert "/bcdata.sgs.4389/dados" in str(pedidos[0].url)
    assert "ultimos" not in str(pedidos[0].url)
    assert params["dataInicial"] == "01/09/2026"
    assert params["dataFinal"] == "21/10/2026"
    assert [p.data for p in pontos] == ["16/10/2026", "19/10/2026"]
    assert pontos[1].valor == 13.65


@pytest.mark.parametrize(
    ("status", "texto", "trecho"),
    [
        (404, "nao existe", "moeda ou período inválido"),
        (500, "erro", "indisponível"),
        (200, "<html>Requisição inválida</html>", "indisponível"),  # o WAF do BCB devolve HTML
    ],
)
async def test_falha_vira_mercado_error_sem_vazar_url(rede, status, texto, trecho):
    _, estado = rede
    estado.update(status=status, texto=texto)

    with pytest.raises(MercadoError, match=trecho) as erro:
        await awesomeapi.cotacoes_atuais(["USD-BRL"])

    assert "http" not in str(erro.value)

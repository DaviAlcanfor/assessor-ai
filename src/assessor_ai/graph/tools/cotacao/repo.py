import functools
from collections.abc import Awaitable, Callable
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from langchain_core.tools import StructuredTool

from assessor_ai.graph.tools.cotacao.schemas import (
    ConverterMoedaArgs,
    CotacaoAtualArgs,
    CotacaoHistoricaArgs,
    Indicador,
    IndicadorEconomicoArgs,
    PtaxDolarArgs,
    SimularInvestimentoArgs,
)
from assessor_ai.graph.tools.response import Response, ToolResponse
from assessor_ai.infra.mercado import MercadoError, awesomeapi, bcb
from assessor_ai.infra.mercado.schemas import PontoSerie
from assessor_ai.logging import get_logger

logger = get_logger("mercado")

_FUSO = ZoneInfo("America/Sao_Paulo")
_MAX_PONTOS = 31  # o LLM não precisa de 360 pontos pra descrever uma tendência
_MAX_DIAS_HISTORICO = 360

# série no SGS do Banco Central: código, nome, unidade, e se é mensal (um ponto por mês) ou diária
_INDICADORES: dict[Indicador, tuple[int, str, str, bool]] = {
    "selic":    (432,   "Meta da taxa Selic",          "% ao ano",      False),
    "cdi":      (4389,  "CDI anualizado",              "% ao ano",      False),
    "ipca":     (433,   "IPCA (variação mensal)",      "% no mês",      True),
    "ipca_12m": (13522, "IPCA acumulado em 12 meses",  "% em 12 meses", True),
}
_JANELA_DIARIA_DIAS = 45  # ≥ 12 pontos mesmo com feriados

_AVISO_SIMULACAO = (
    "Simulação bruta: taxa constante, sem imposto de renda, IOF nem taxas, e sem garantia de "
    "rentabilidade. Não é recomendação de investimento."
)


def _como_resposta(func: Callable[..., Awaitable[ToolResponse]]) -> Callable[..., Awaitable[ToolResponse]]:
    """Erro de mercado vira `Response.error` com mensagem segura; o resto é logado e fica genérico."""

    @functools.wraps(func)
    async def wrapper(*args: object, **kwargs: object) -> ToolResponse:
        try:
            return await func(*args, **kwargs)
        except (MercadoError, ValueError) as e:
            return Response.error(e)
        except Exception:
            logger.exception("MERCADO ERRO | %s", func.__name__)
            return Response.error("Falha inesperada ao consultar o mercado.")

    return wrapper


def _hoje() -> date:
    return datetime.now(_FUSO).date()


def _data(texto: str) -> date:
    try:
        return date.fromisoformat(texto)
    except ValueError:
        raise ValueError(f"Data inválida: '{texto}'. Use o formato YYYY-MM-DD.") from None


def _moeda(codigo: str) -> str:
    codigo = codigo.strip().upper()
    if not (2 <= len(codigo) <= 5 and codigo.isalpha()):
        raise ValueError(f"Código de moeda inválido: '{codigo}'. Use códigos como USD, EUR, BTC.")
    return codigo


def _amostrar[T](pontos: list[T]) -> list[T]:
    """No máximo `_MAX_PONTOS`, espaçados por igual, sempre mantendo o primeiro e o último."""

    if len(pontos) <= _MAX_PONTOS:
        return pontos
    passo = (len(pontos) - 1) / (_MAX_PONTOS - 1)
    return [pontos[round(i * passo)] for i in range(_MAX_PONTOS)]


async def _ultimos_da_serie(indicador: Indicador, ultimos: int) -> list[PontoSerie]:
    """Os `ultimos` pontos até hoje. A janela termina hoje porque a Selic traz datas futuras (vigência
    já anunciada), e o mês corrente do IPCA ainda não saiu: a janela mensal sobra um mês de folga."""

    codigo, _, _, mensal = _INDICADORES[indicador]
    dias = 31 * (ultimos + 2) if mensal else _JANELA_DIARIA_DIAS
    hoje = _hoje()
    return (await bcb.serie_sgs(codigo, hoje - timedelta(days=dias), hoje))[-ultimos:]


class CotacaoRepo:
    """Dados de mercado públicos (AwesomeAPI e Banco Central). Sem escopo de usuário e sem banco:
    cada método público é uma tool do agente financeiro."""

    @_como_resposta
    async def cotacao_atual(self, moedas: list[str]) -> ToolResponse:
        """Cotação atual (compra, venda, variação do dia, máxima e mínima) de moedas contra o real."""

        codigos = list(dict.fromkeys(_moeda(m) for m in moedas))
        cotacoes = await awesomeapi.cotacoes_atuais([f"{c}-BRL" for c in codigos])

        return Response.ok(
            cotacoes=[
                {
                    "moeda": c.code,
                    "nome": c.name,
                    "compra": c.bid,
                    "venda": c.ask,
                    "variacao_dia_pct": c.pct_change,
                    "maxima": c.high,
                    "minima": c.low,
                    "atualizado_em": c.create_date,
                }
                for c in cotacoes.values()
            ]
        )

    @_como_resposta
    async def cotacao_historica(self, moeda: str, data_inicio: str, data_fim: str) -> ToolResponse:
        """Cotação diária de uma moeda contra o real num período, com resumo (mínima, máxima, média e variação)."""

        codigo = _moeda(moeda)
        inicio, fim = _data(data_inicio), _data(data_fim)

        if fim < inicio:
            raise ValueError("A data final é anterior à inicial.")
        if (fim - inicio).days + 1 > _MAX_DIAS_HISTORICO:
            raise ValueError(f"Período longo demais: no máximo {_MAX_DIAS_HISTORICO} dias por consulta.")

        dias = sorted(await awesomeapi.cotacoes_diarias(f"{codigo}-BRL", inicio, fim), key=lambda d: d.timestamp)
        if not dias:
            return Response.error("Não há cotação nesse período.")

        pontos = [
            {"data": datetime.fromtimestamp(d.timestamp, tz=_FUSO).date().isoformat(), "cotacao": d.bid}
            for d in dias
        ]
        valores = [d.bid for d in dias]

        return Response.ok(
            moeda=codigo,
            resumo={
                "primeira": valores[0],
                "ultima": valores[-1],
                "minima": min(valores),
                "maxima": max(valores),
                "media": round(sum(valores) / len(valores), 4),
                "variacao_pct": round((valores[-1] / valores[0] - 1) * 100, 2),
                "dias_com_cotacao": len(valores),
            },
            pontos=_amostrar(pontos),
        )

    @_como_resposta
    async def ptax_dolar(self, data_inicio: str, data_fim: str | None = None) -> ToolResponse:
        """PTAX: cotação oficial de fechamento do dólar (Banco Central) de um dia ou período. Não existe em fim de semana e feriado."""

        inicio = _data(data_inicio)
        fim = _data(data_fim) if data_fim else inicio

        if fim < inicio:
            raise ValueError("A data final é anterior à inicial.")

        boletins = await bcb.ptax_dolar(inicio, fim)
        observacao = None

        if not boletins and inicio == fim:
            # Dia sem boletim (fim de semana/feriado): devolve o último fechamento anterior.
            boletins = (await bcb.ptax_dolar(inicio - timedelta(days=7), inicio))[-1:]
            observacao = "Não há PTAX nesse dia (fim de semana ou feriado); este é o último fechamento anterior."

        if not boletins:
            return Response.error("Não há PTAX nesse período (fim de semana ou feriado).")

        return Response.ok(
            ptax=[
                {"data": b.data_hora[:10], "compra": b.compra, "venda": b.venda}
                for b in _amostrar(boletins)
            ],
            observacao=observacao,
        )

    @_como_resposta
    async def converter_moeda(self, valor: float, de: str, para: str) -> ToolResponse:
        """Converte um valor entre duas moedas (ex.: dólares em reais) pela cotação de compra atual."""

        origem, destino = _moeda(de), _moeda(para)
        if origem == destino:
            return Response.ok(valor_original=valor, valor_convertido=valor, taxa=1.0)

        # Tudo passa pelo real: USD→EUR = USD→BRL ÷ EUR→BRL.
        pares = [f"{m}-BRL" for m in (origem, destino) if m != "BRL"]
        cotacoes = await awesomeapi.cotacoes_atuais(pares)
        em_reais = {c.code: c.bid for c in cotacoes.values()} | {"BRL": 1.0}

        taxa = em_reais[origem] / em_reais[destino]

        return Response.ok(
            valor_original=valor,
            moeda_origem=origem,
            moeda_destino=destino,
            taxa=round(taxa, 6),
            valor_convertido=round(valor * taxa, 2),
            observacao="Cotação de compra no momento da consulta; spread e impostos de câmbio não incluídos.",
        )

    @_como_resposta
    async def indicador_economico(self, indicador: Indicador, ultimos: int = 1) -> ToolResponse:
        """Indicadores do Banco Central: Selic, CDI e inflação (IPCA mensal ou acumulada em 12 meses)."""

        _, nome, unidade, _ = _INDICADORES[indicador]
        pontos = await _ultimos_da_serie(indicador, ultimos)
        if not pontos:
            return Response.error("O Banco Central não devolveu valores para esse indicador.")

        return Response.ok(
            indicador=nome,
            unidade=unidade,
            valores=[{"data": p.dia.isoformat(), "valor": p.valor} for p in pontos],
        )

    @_como_resposta
    async def simular_investimento(
        self,
        valor_inicial: float,
        meses: int,
        aporte_mensal: float = 0,
        taxa_anual_percentual: float | None = None,
        indicador: str | None = None,
        percentual_do_indicador: float = 100,
    ) -> ToolResponse:
        """Simula juros compostos: quanto vira um valor inicial com aportes mensais, a uma taxa anual ou a um % do CDI/Selic."""

        if (taxa_anual_percentual is None) == (indicador is None):
            raise ValueError("Informe a taxa anual OU o indicador (cdi/selic), não os dois nem nenhum.")

        if indicador is not None:
            pontos = await _ultimos_da_serie("cdi" if indicador == "cdi" else "selic", 1)
            if not pontos:
                raise MercadoError(f"Não consegui a taxa atual do {indicador.upper()} agora.")
            ponto = pontos[0]
            taxa_anual = ponto.valor * percentual_do_indicador / 100
            base = f"{percentual_do_indicador:g}% do {indicador.upper()} ({ponto.valor:g}% a.a.)"
        else:
            assert taxa_anual_percentual is not None
            taxa_anual = taxa_anual_percentual
            base = f"{taxa_anual:g}% ao ano"

        taxa_mensal = (1 + taxa_anual / 100) ** (1 / 12) - 1
        saldo = valor_inicial
        for _ in range(meses):
            saldo = saldo * (1 + taxa_mensal) + aporte_mensal  # aporte entra no fim do mês, depois do rendimento

        investido = valor_inicial + aporte_mensal * meses

        return Response.ok(
            taxa_usada=base,
            taxa_anual_pct=round(taxa_anual, 4),
            meses=meses,
            total_investido=round(investido, 2),
            valor_final_bruto=round(saldo, 2),
            rendimento_bruto=round(saldo - investido, 2),
            aviso=_AVISO_SIMULACAO,
        )

    def as_tools(self) -> list[StructuredTool]:
        return [
            StructuredTool.from_function(
                coroutine=self.cotacao_atual, name="cotacao_atual", args_schema=CotacaoAtualArgs
            ),
            StructuredTool.from_function(
                coroutine=self.cotacao_historica, name="cotacao_historica", args_schema=CotacaoHistoricaArgs
            ),
            StructuredTool.from_function(
                coroutine=self.ptax_dolar, name="ptax_dolar", args_schema=PtaxDolarArgs
            ),
            StructuredTool.from_function(
                coroutine=self.converter_moeda, name="converter_moeda", args_schema=ConverterMoedaArgs
            ),
            StructuredTool.from_function(
                coroutine=self.indicador_economico, name="indicador_economico", args_schema=IndicadorEconomicoArgs
            ),
            StructuredTool.from_function(
                coroutine=self.simular_investimento,
                name="simular_investimento",
                args_schema=SimularInvestimentoArgs,
            ),
        ]


__all__ = ["CotacaoRepo"]

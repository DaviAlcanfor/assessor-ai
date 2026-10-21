"""Casos de uso de dados de mercado (cotação, PTAX, Selic/CDI/IPCA e simulação de investimento).

Sem repository: não há persistência, só os clientes das APIs públicas (`infra/mercado/`). Os métodos
devolvem dados tipados e levantam `DadosInvalidos` (entrada ruim) ou `MercadoError` (API fora do ar);
quem fala com o LLM é `graph/tools/mercado/tools.py`.
"""

from datetime import date, datetime, timedelta
from typing import Literal, NamedTuple, TypedDict
from zoneinfo import ZoneInfo

from app.domain.errors import DadosInvalidos
from app.infra.mercado import MercadoError, awesomeapi, ptax, sgs
from app.infra.mercado.schemas import PontoSerie

Indicador = Literal["selic", "cdi", "ipca", "ipca_12m"]

_FUSO = ZoneInfo("America/Sao_Paulo")
_MAX_PONTOS = 31  # o LLM não precisa de 360 pontos pra descrever uma tendência
_MAX_DIAS_HISTORICO = 360
_JANELA_DIARIA_DIAS = 45  # ≥ 12 pontos mesmo com feriados

_AVISO_SIMULACAO = (
    "Simulação bruta: taxa constante, sem imposto de renda, IOF nem taxas, e sem garantia de "
    "rentabilidade. Não é recomendação de investimento."
)


class SerieSGS(NamedTuple):
    """Uma série do SGS (Banco Central) exposta como indicador."""

    codigo: int
    nome: str
    unidade: str
    mensal: bool  # um ponto por mês (IPCA); senão é diária (Selic, CDI)


_SERIES: dict[Indicador, SerieSGS] = {
    "selic":    SerieSGS(codigo=432,   nome="Meta da taxa Selic",         unidade="% ao ano",      mensal=False),
    "cdi":      SerieSGS(codigo=4389,  nome="CDI anualizado",             unidade="% ao ano",      mensal=False),
    "ipca":     SerieSGS(codigo=433,   nome="IPCA (variação mensal)",     unidade="% no mês",      mensal=True),
    "ipca_12m": SerieSGS(codigo=13522, nome="IPCA acumulado em 12 meses", unidade="% em 12 meses", mensal=True),
}


class CotacaoMoeda(TypedDict):
    moeda:            str
    nome:             str
    compra:           float
    venda:            float
    variacao_dia_pct: float
    maxima:           float
    minima:           float
    atualizado_em:    str


class PontoCotacao(TypedDict):
    data:     str
    cotacao:  float


class ResumoHistorico(TypedDict):
    primeira:         float
    ultima:           float
    minima:           float
    maxima:           float
    media:            float
    variacao_pct:     float
    dias_com_cotacao: int


class HistoricoCotacao(TypedDict):
    moeda:  str
    resumo: ResumoHistorico
    pontos: list[PontoCotacao]


class FechamentoPtax(TypedDict):
    data:   str
    compra: float
    venda:  float


class ResultadoPtax(TypedDict):
    ptax:       list[FechamentoPtax]
    observacao: str | None


class Conversao(TypedDict):
    valor_original:    float
    moeda_origem:      str
    moeda_destino:     str
    taxa:              float
    valor_convertido:  float
    observacao:        str | None


class ValorIndicador(TypedDict):
    data:  str
    valor: float


class ResultadoIndicador(TypedDict):
    indicador: str
    unidade:   str
    valores:   list[ValorIndicador]


class Simulacao(TypedDict):
    taxa_usada:        str
    taxa_anual_pct:    float
    meses:             int
    total_investido:   float
    valor_final_bruto: float
    rendimento_bruto:  float
    aviso:             str


def _hoje() -> date:
    return datetime.now(_FUSO).date()


def _data(texto: str) -> date:
    try:
        return date.fromisoformat(texto)
    except ValueError:
        raise DadosInvalidos(f"Data inválida: '{texto}'. Use o formato YYYY-MM-DD.") from None


def _moeda(codigo: str) -> str:
    codigo = codigo.strip().upper()
    if not (2 <= len(codigo) <= 5 and codigo.isalpha()):
        raise DadosInvalidos(f"Código de moeda inválido: '{codigo}'. Use códigos como USD, EUR, BTC.")
    return codigo


def _amostrar[T](pontos: list[T]) -> list[T]:
    """No máximo `_MAX_PONTOS`, espaçados por igual, sempre mantendo o primeiro e o último."""

    if len(pontos) <= _MAX_PONTOS:
        return pontos
    passo = (len(pontos) - 1) / (_MAX_PONTOS - 1)
    return [pontos[round(i * passo)] for i in range(_MAX_PONTOS)]


class MercadoService:
    """Dados de mercado públicos (AwesomeAPI e Banco Central). Sem escopo de usuário e sem banco."""

    async def cotacao_atual(self, moedas: list[str]) -> list[CotacaoMoeda]:
        """Compra, venda, variação do dia, máxima e mínima de cada moeda contra o real."""

        codigos = list(dict.fromkeys(_moeda(m) for m in moedas))
        cotacoes = await awesomeapi.cotacoes_atuais([f"{c}-BRL" for c in codigos])

        return [
            CotacaoMoeda(
                moeda=c.code,
                nome=c.name,
                compra=c.bid,
                venda=c.ask,
                variacao_dia_pct=c.pct_change,
                maxima=c.high,
                minima=c.low,
                atualizado_em=c.create_date.isoformat(sep=" "),
            )
            for c in cotacoes.values()
        ]

    async def cotacao_historica(self, moeda: str, data_inicio: str, data_fim: str) -> HistoricoCotacao:
        codigo = _moeda(moeda)
        inicio, fim = _data(data_inicio), _data(data_fim)

        if fim < inicio:
            raise DadosInvalidos("A data final é anterior à inicial.")
        if (fim - inicio).days + 1 > _MAX_DIAS_HISTORICO:
            raise DadosInvalidos(f"Período longo demais: no máximo {_MAX_DIAS_HISTORICO} dias por consulta.")

        dias = sorted(await awesomeapi.cotacoes_diarias(f"{codigo}-BRL", inicio, fim), key=lambda d: d.timestamp)
        if not dias:
            raise DadosInvalidos("Não há cotação nesse período.")

        pontos = [
            PontoCotacao(data=d.timestamp.astimezone(_FUSO).date().isoformat(), cotacao=d.bid) for d in dias
        ]
        valores = [d.bid for d in dias]

        return HistoricoCotacao(
            moeda=codigo,
            resumo=ResumoHistorico(
                primeira=valores[0],
                ultima=valores[-1],
                minima=min(valores),
                maxima=max(valores),
                media=round(sum(valores) / len(valores), 4),
                variacao_pct=round((valores[-1] / valores[0] - 1) * 100, 2),
                dias_com_cotacao=len(valores),
            ),
            pontos=_amostrar(pontos),
        )

    async def ptax_dolar(self, data_inicio: str, data_fim: str | None = None) -> ResultadoPtax:
        inicio = _data(data_inicio)
        fim = _data(data_fim) if data_fim else inicio

        if fim < inicio:
            raise DadosInvalidos("A data final é anterior à inicial.")

        boletins = await ptax.dolar(inicio, fim)
        observacao = None

        if not boletins and inicio == fim:
            # Dia sem boletim (fim de semana/feriado): devolve o último fechamento anterior.
            boletins = (await ptax.dolar(inicio - timedelta(days=7), inicio))[-1:]
            observacao = "Não há PTAX nesse dia (fim de semana ou feriado); este é o último fechamento anterior."

        if not boletins:
            raise DadosInvalidos("Não há PTAX nesse período (fim de semana ou feriado).")

        return ResultadoPtax(
            ptax=[
                FechamentoPtax(data=b.data_hora.date().isoformat(), compra=b.compra, venda=b.venda)
                for b in _amostrar(boletins)
            ],
            observacao=observacao,
        )

    async def converter_moeda(self, valor: float, de: str, para: str) -> Conversao:
        origem, destino = _moeda(de), _moeda(para)
        if origem == destino:
            return Conversao(
                valor_original=valor, moeda_origem=origem, moeda_destino=destino,
                taxa=1.0, valor_convertido=valor, observacao=None,
            )

        # Tudo passa pelo real: USD→EUR = USD→BRL ÷ EUR→BRL.
        pares = [f"{m}-BRL" for m in (origem, destino) if m != "BRL"]
        cotacoes = await awesomeapi.cotacoes_atuais(pares)
        em_reais = {c.code: c.bid for c in cotacoes.values()} | {"BRL": 1.0}

        taxa = em_reais[origem] / em_reais[destino]

        return Conversao(
            valor_original=valor,
            moeda_origem=origem,
            moeda_destino=destino,
            taxa=round(taxa, 6),
            valor_convertido=round(valor * taxa, 2),
            observacao="Cotação de compra no momento da consulta; spread e impostos de câmbio não incluídos.",
        )

    async def _ultimos_da_serie(self, indicador: Indicador, ultimos: int) -> list[PontoSerie]:
        """Os `ultimos` pontos até hoje. A janela termina hoje porque a Selic traz datas futuras (vigência
        já anunciada), e o mês corrente do IPCA ainda não saiu: a janela mensal sobra um mês de folga."""

        serie = _SERIES[indicador]
        dias = 31 * (ultimos + 2) if serie.mensal else _JANELA_DIARIA_DIAS
        hoje = _hoje()

        return (await sgs.serie(serie.codigo, hoje - timedelta(days=dias), hoje))[-ultimos:]

    async def indicador_economico(self, indicador: Indicador, ultimos: int = 1) -> ResultadoIndicador:
        serie = _SERIES[indicador]
        pontos = await self._ultimos_da_serie(indicador, ultimos)
        if not pontos:
            raise MercadoError("O Banco Central não devolveu valores para esse indicador.")

        return ResultadoIndicador(
            indicador=serie.nome,
            unidade=serie.unidade,
            valores=[ValorIndicador(data=p.data.isoformat(), valor=p.valor) for p in pontos],
        )

    async def simular_investimento(
        self,
        valor_inicial: float,
        meses: int,
        aporte_mensal: float = 0,
        taxa_anual_percentual: float | None = None,
        indicador: Literal["cdi", "selic"] | None = None,
        percentual_do_indicador: float = 100,
    ) -> Simulacao:
        if (taxa_anual_percentual is None) == (indicador is None):
            raise DadosInvalidos("Informe a taxa anual OU o indicador (cdi/selic), não os dois nem nenhum.")

        if indicador is not None:
            pontos = await self._ultimos_da_serie(indicador, 1)
            if not pontos:
                raise MercadoError(f"Não consegui a taxa atual do {indicador.upper()} agora.")
            taxa_anual = pontos[0].valor * percentual_do_indicador / 100
            base = f"{percentual_do_indicador:g}% do {indicador.upper()} ({pontos[0].valor:g}% a.a.)"
        else:
            assert taxa_anual_percentual is not None
            taxa_anual = taxa_anual_percentual
            base = f"{taxa_anual:g}% ao ano"

        taxa_mensal = (1 + taxa_anual / 100) ** (1 / 12) - 1
        saldo = valor_inicial
        for _ in range(meses):
            saldo = saldo * (1 + taxa_mensal) + aporte_mensal  # aporte entra no fim do mês, depois do rendimento

        investido = valor_inicial + aporte_mensal * meses

        return Simulacao(
            taxa_usada=base,
            taxa_anual_pct=round(taxa_anual, 4),
            meses=meses,
            total_investido=round(investido, 2),
            valor_final_bruto=round(saldo, 2),
            rendimento_bruto=round(saldo - investido, 2),
            aviso=_AVISO_SIMULACAO,
        )


mercado_service = MercadoService()


__all__ = ["Indicador", "MercadoService", "mercado_service"]

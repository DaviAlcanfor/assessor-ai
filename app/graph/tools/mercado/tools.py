from typing import ClassVar, Literal

from app.graph.tools.base import Schemas, ToolSet
from app.graph.tools.mercado.schemas import (
    ConverterMoedaArgs,
    CotacaoAtualArgs,
    CotacaoHistoricaArgs,
    IndicadorEconomicoArgs,
    PtaxDolarArgs,
    SimularInvestimentoArgs,
)
from app.graph.tools.response import Response, ToolResponse
from app.services.mercado_service import Indicador, MercadoService, mercado_service


class MercadoTools(ToolSet):
    """Dados de mercado públicos (AwesomeAPI e Banco Central) pro agente financeiro. Sem escopo de
    usuário e sem banco; a lógica está em `MercadoService`."""

    schemas: ClassVar[Schemas] = {
        "cotacao_atual": CotacaoAtualArgs,
        "cotacao_historica": CotacaoHistoricaArgs,
        "ptax_dolar": PtaxDolarArgs,
        "converter_moeda": ConverterMoedaArgs,
        "indicador_economico": IndicadorEconomicoArgs,
        "simular_investimento": SimularInvestimentoArgs,
    }

    def __init__(self, service: MercadoService | None = None) -> None:
        self.service = service or mercado_service

    async def cotacao_atual(self, moedas: list[str]) -> ToolResponse:
        """Cotação atual (compra, venda, variação do dia, máxima e mínima) de moedas contra o real."""

        return Response.ok(cotacoes=await self.service.cotacao_atual(moedas))

    async def cotacao_historica(self, moeda: str, data_inicio: str, data_fim: str) -> ToolResponse:
        """Cotação diária de uma moeda contra o real num período, com resumo (mínima, máxima, média e variação)."""

        return Response.ok(**await self.service.cotacao_historica(moeda, data_inicio, data_fim))

    async def ptax_dolar(self, data_inicio: str, data_fim: str | None = None) -> ToolResponse:
        """PTAX: cotação oficial de fechamento do dólar (Banco Central) de um dia ou período. Não existe em fim de semana e feriado."""

        return Response.ok(**await self.service.ptax_dolar(data_inicio, data_fim))

    async def converter_moeda(self, valor: float, de: str, para: str) -> ToolResponse:
        """Converte um valor entre duas moedas (ex.: dólares em reais) pela cotação de compra atual."""

        return Response.ok(**await self.service.converter_moeda(valor, de, para))

    async def indicador_economico(self, indicador: Indicador, ultimos: int = 1) -> ToolResponse:
        """Indicadores do Banco Central: Selic, CDI e inflação (IPCA mensal ou acumulada em 12 meses)."""

        return Response.ok(**await self.service.indicador_economico(indicador, ultimos))

    async def simular_investimento(
        self,
        valor_inicial: float,
        meses: int,
        aporte_mensal: float = 0,
        taxa_anual_percentual: float | None = None,
        indicador: Literal["cdi", "selic"] | None = None,
        percentual_do_indicador: float = 100,
    ) -> ToolResponse:
        """Simula juros compostos: quanto vira um valor inicial com aportes mensais, a uma taxa anual ou a um % do CDI/Selic."""

        return Response.ok(
            **await self.service.simular_investimento(
                valor_inicial, meses, aporte_mensal, taxa_anual_percentual, indicador, percentual_do_indicador
            )
        )


__all__ = ["MercadoTools"]

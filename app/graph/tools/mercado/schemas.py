from typing import Literal

from pydantic import BaseModel, Field

from app.services.mercado_service import Indicador


class CotacaoAtualArgs(BaseModel):
    moedas: list[str] = Field(
        default=["USD"],
        min_length=1,
        max_length=5,
        description="Códigos das moedas, sempre cotadas contra o real: USD (dólar), EUR (euro), GBP, BTC...",
    )


class CotacaoHistoricaArgs(BaseModel):
    moeda: str = Field(..., description="Código da moeda, cotada contra o real: USD, EUR, BTC...")
    data_inicio: str = Field(..., description="Data inicial no formato YYYY-MM-DD.")
    data_fim: str = Field(..., description="Data final no formato YYYY-MM-DD (no máximo 360 dias depois da inicial).")


class PtaxDolarArgs(BaseModel):
    data_inicio: str = Field(..., description="Data inicial no formato YYYY-MM-DD.")
    data_fim: str | None = Field(
        default=None, description="Data final YYYY-MM-DD. Se ausente, usa só o dia de data_inicio."
    )


class ConverterMoedaArgs(BaseModel):
    valor: float = Field(..., gt=0, description="Quantia na moeda de origem.")
    de: str = Field(..., description="Código da moeda de origem: USD, EUR, BRL...")
    para: str = Field(..., description="Código da moeda de destino: BRL, USD, EUR...")


class IndicadorEconomicoArgs(BaseModel):
    indicador: Indicador = Field(
        ...,
        description=(
            "selic = meta da taxa Selic (% ao ano); cdi = CDI (% ao ano); ipca = inflação do último mês; "
            "ipca_12m = inflação acumulada em 12 meses."
        ),
    )
    ultimos: int = Field(default=1, ge=1, le=12, description="Quantos valores recentes devolver (1 = só o mais recente).")


class SimularInvestimentoArgs(BaseModel):
    valor_inicial: float = Field(..., ge=0, description="Quantia aplicada no início, em reais.")
    aporte_mensal: float = Field(default=0, ge=0, description="Quanto é aportado todo mês, em reais.")
    meses: int = Field(..., ge=1, le=600, description="Prazo da simulação em meses.")
    taxa_anual_percentual: float | None = Field(
        default=None, ge=0, le=200, description="Taxa anual em %, ex.: 10.5. Use ESTE campo OU `indicador`."
    )
    indicador: Literal["cdi", "selic"] | None = Field(
        default=None, description="Usa a taxa atual do CDI ou da Selic no lugar de `taxa_anual_percentual`."
    )
    percentual_do_indicador: float = Field(
        default=100, gt=0, le=300, description="Só com `indicador`: quanto dele rende, ex.: 110 para '110% do CDI'."
    )

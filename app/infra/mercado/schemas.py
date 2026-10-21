from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field


def _data_br(valor: object) -> object:
    """`dd/mm/aaaa`, o formato das séries do SGS. Qualquer outra coisa segue pro validador do pydantic."""

    if isinstance(valor, str) and valor.count("/") == 2:
        dia, mes, ano = valor.split("/")
        return date(int(ano), int(mes), int(dia))
    return valor


DataBR = Annotated[date, BeforeValidator(_data_br)]


class _Resposta(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class CotacaoAtual(_Resposta):
    """Uma entrada de `/json/last/`. Números e data chegam como string; o pydantic converte."""

    code: str
    codein: str
    name: str
    bid: float
    ask: float
    high: float
    low: float
    pct_change: float = Field(alias="pctChange")
    create_date: datetime  # horário de Brasília, sem fuso na resposta


class CotacaoDia(_Resposta):
    """Uma entrada de `/json/daily/`; só a primeira traz code/name, por isso não pedimos."""

    bid: float
    ask: float
    high: float
    low: float
    timestamp: datetime  # chega como epoch em string; vira datetime em UTC


class PtaxDia(_Resposta):
    compra: float = Field(alias="cotacaoCompra")
    venda: float = Field(alias="cotacaoVenda")
    data_hora: datetime = Field(alias="dataHoraCotacao")


class PontoSerie(_Resposta):
    data: DataBR
    valor: float

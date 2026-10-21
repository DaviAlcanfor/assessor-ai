from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class _Resposta(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class CotacaoAtual(_Resposta):
    """Uma entrada de `/json/last/`. Os números chegam como string; o pydantic converte."""

    code: str
    codein: str
    name: str
    bid: float
    ask: float
    high: float
    low: float
    pct_change: float = Field(alias="pctChange")
    create_date: str


class CotacaoDia(_Resposta):
    """Uma entrada de `/json/daily/`; só a primeira traz code/name, por isso não pedimos."""

    bid: float
    ask: float
    high: float
    low: float
    timestamp: int


class PtaxDia(_Resposta):
    compra: float = Field(alias="cotacaoCompra")
    venda: float = Field(alias="cotacaoVenda")
    data_hora: str = Field(alias="dataHoraCotacao")


class PontoSerie(_Resposta):
    data: str  # dd/mm/aaaa
    valor: float

    @property
    def dia(self) -> date:
        dia, mes, ano = self.data.split("/")
        return date(int(ano), int(mes), int(dia))

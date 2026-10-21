"""Banco Central: PTAX (dólar oficial de fechamento) e séries do SGS (Selic, CDI, IPCA). Sem chave."""

from datetime import date

from app.infra.mercado.client import MercadoClient
from app.infra.mercado.schemas import PontoSerie, PtaxDia
from app.settings import settings


class PtaxClient(MercadoClient):
    """API OData do BCB. Fim de semana e feriado não têm boletim."""

    alvo = "bcb"

    async def dolar(self, inicio: date, fim: date) -> list[PtaxDia]:
        """Boletins de fechamento do dólar entre as datas, do mais antigo pro mais recente."""

        url = self._url(
            "CotacaoDolarPeriodo(dataInicial=@dataInicial,dataFinalCotacao=@dataFinalCotacao)",
            # OData: datas em mês-dia-ano entre aspas simples; sem `$orderby` (ordena-se aqui embaixo).
            query_crua=f"@dataInicial='{inicio:%m-%d-%Y}'&@dataFinalCotacao='{fim:%m-%d-%Y}'&$format=json",
        )
        corpo = await self._objeto(url, ttl_s=settings.mercado.ttl_historico_s)
        boletins = corpo["value"]
        if not isinstance(boletins, list):
            return []
        return sorted((PtaxDia.model_validate(b) for b in boletins), key=lambda b: b.data_hora)


class SgsClient(MercadoClient):
    """Séries temporais do SGS (Selic, CDI, IPCA...)."""

    alvo = "bcb"

    async def serie(self, codigo: int, inicio: date, fim: date) -> list[PontoSerie]:
        """Pontos da série entre as datas, do mais antigo pro mais recente.

        Sempre por janela de datas, nunca por `/ultimos/N`: esse formato volta em ordem crescente numa
        série e decrescente em outra, inclui datas futuras (vigência já anunciada da Selic) e o BCB o
        recusa em séries diárias desde 2025 (devolve uma página HTML, não JSON)."""

        url = self._url(
            f"bcdata.sgs.{codigo}/dados",
            params={"formato": "json", "dataInicial": f"{inicio:%d/%m/%Y}", "dataFinal": f"{fim:%d/%m/%Y}"},
        )
        corpo = await self._lista(url, ttl_s=settings.mercado.ttl_historico_s)
        return sorted((PontoSerie.model_validate(p) for p in corpo), key=lambda p: p.data)


ptax = PtaxClient(settings.mercado.bcb_ptax_base_url)
sgs = SgsClient(settings.mercado.bcb_sgs_base_url)

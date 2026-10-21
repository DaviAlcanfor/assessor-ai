"""AwesomeAPI: cotação de moedas contra o real, em tempo (quase) real e diária. Sem chave."""

from datetime import date

from app.infra.mercado.client import MercadoClient
from app.infra.mercado.schemas import CotacaoAtual, CotacaoDia
from app.settings import settings

_MAX_DIAS = 360  # teto do endpoint diário


class AwesomeApiClient(MercadoClient):
    alvo = "awesomeapi"

    async def cotacoes_atuais(self, pares: list[str]) -> dict[str, CotacaoAtual]:
        """`pares` no formato `USD-BRL`. A chave do retorno é o par sem hífen (`USDBRL`)."""

        url = self._url(f"json/last/{','.join(pares)}")
        corpo = await self._objeto(url, ttl_s=settings.mercado.ttl_atual_s)
        return {chave: CotacaoAtual.model_validate(item) for chave, item in corpo.items()}

    async def cotacoes_diarias(self, par: str, inicio: date, fim: date) -> list[CotacaoDia]:
        """Uma cotação por dia com negociação, da mais recente pra mais antiga (ordem da API)."""

        dias = min((fim - inicio).days + 1, _MAX_DIAS)
        url = self._url(
            f"json/daily/{par}/{dias}",
            params={"start_date": f"{inicio:%Y%m%d}", "end_date": f"{fim:%Y%m%d}"},
        )
        corpo = await self._lista(url, ttl_s=settings.mercado.ttl_historico_s)
        return [CotacaoDia.model_validate(item) for item in corpo]


awesomeapi = AwesomeApiClient(settings.mercado.awesomeapi_base_url)

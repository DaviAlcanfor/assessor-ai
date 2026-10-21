"""AwesomeAPI: cotação de moedas contra o real, em tempo (quase) real e diária. Sem chave."""

from datetime import date

from assessor_ai.infra.mercado.http import buscar_json
from assessor_ai.infra.mercado.schemas import CotacaoAtual, CotacaoDia
from assessor_ai.settings import settings

_MAX_DIAS = 360  # teto do endpoint diário


async def cotacoes_atuais(pares: list[str]) -> dict[str, CotacaoAtual]:
    """`pares` no formato `USD-BRL`. A chave do retorno é o par sem hífen (`USDBRL`)."""

    cfg = settings.mercado
    dados = await buscar_json(
        "awesomeapi", f"{cfg.awesomeapi_base_url}/json/last/{','.join(pares)}", ttl_s=cfg.ttl_atual_s
    )
    return {chave: CotacaoAtual.model_validate(item) for chave, item in dados.items()}


async def cotacoes_diarias(par: str, inicio: date, fim: date) -> list[CotacaoDia]:
    """Uma cotação por dia útil do período, da mais recente pra mais antiga (ordem da API)."""

    cfg = settings.mercado
    dias = min((fim - inicio).days + 1, _MAX_DIAS)
    dados = await buscar_json(
        "awesomeapi",
        f"{cfg.awesomeapi_base_url}/json/daily/{par}/{dias}",
        params={"start_date": f"{inicio:%Y%m%d}", "end_date": f"{fim:%Y%m%d}"},
        ttl_s=cfg.ttl_historico_s,
    )
    return [CotacaoDia.model_validate(item) for item in dados]

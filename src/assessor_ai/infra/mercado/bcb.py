"""Banco Central: PTAX (dólar oficial de fechamento) e séries do SGS (Selic, CDI, IPCA). Sem chave."""

from datetime import date

from assessor_ai.infra.mercado.http import buscar_json
from assessor_ai.infra.mercado.schemas import PontoSerie, PtaxDia
from assessor_ai.settings import settings


async def ptax_dolar(inicio: date, fim: date) -> list[PtaxDia]:
    """Boletim de fechamento do dólar por dia útil, do mais antigo pro mais recente. Fim de semana e
    feriado não têm boletim, então um período sem dia útil volta vazio."""

    cfg = settings.mercado
    # A query vai crua na URL de propósito: o httpx codifica `$format`/`$orderby` como `%24...` e o
    # OData do BCB responde 400 ("system query option ... not supported"). Por isso também não usamos
    # `$orderby`: a ordenação é feita aqui.
    url = (
        f"{cfg.bcb_ptax_base_url}/CotacaoDolarPeriodo(dataInicial=@dataInicial,dataFinalCotacao=@dataFinalCotacao)"
        f"?@dataInicial='{inicio:%m-%d-%Y}'&@dataFinalCotacao='{fim:%m-%d-%Y}'&$format=json"  # mês-dia-ano
    )
    dados = await buscar_json("bcb", url, ttl_s=cfg.ttl_historico_s)
    return sorted((PtaxDia.model_validate(item) for item in dados["value"]), key=lambda b: b.data_hora)


async def serie_sgs(codigo: int, inicio: date, fim: date) -> list[PontoSerie]:
    """Pontos da série `codigo` do SGS entre `inicio` e `fim`, do mais antigo pro mais recente.

    Sempre por janela de datas, nunca por `/ultimos/N`: esse formato volta em ordem crescente numa
    série e decrescente em outra, inclui datas futuras (vigência já anunciada da Selic) e o BCB o
    recusa em séries diárias desde 2025."""

    cfg = settings.mercado
    dados = await buscar_json(
        "bcb",
        f"{cfg.bcb_sgs_base_url}/bcdata.sgs.{codigo}/dados",
        params={"formato": "json", "dataInicial": f"{inicio:%d/%m/%Y}", "dataFinal": f"{fim:%d/%m/%Y}"},
        ttl_s=cfg.ttl_historico_s,
    )
    return sorted((PontoSerie.model_validate(item) for item in dados), key=lambda p: p.dia)

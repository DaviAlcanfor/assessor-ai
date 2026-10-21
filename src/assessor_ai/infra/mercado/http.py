"""
GET JSON das APIs públicas de mercado, com cache em memória e métrica por alvo.

O cliente é aberto por chamada (como o do JeV): sem estado de conexão pra fechar no lifespan, e o
cache absorve a repetição. `MercadoError` carrega mensagem segura pro LLM/usuário — nunca a URL.
"""

import time
from typing import Any

import httpx

from assessor_ai.metrics import medir_externo
from assessor_ai.settings import settings

# O WAF do BCB recusa o User-Agent padrão do httpx/curl quando as chamadas vêm em rajada.
_USER_AGENT = "assessor-ai/0.1"
_MAX_ENTRADAS = 128

# ponytail: cache por processo, FIFO de 128 entradas — com várias instâncias cada uma cacheia a sua;
# vira Redis (infra/redis.py) se a cota da AwesomeAPI apertar.
_cache: dict[tuple[str, tuple[tuple[str, str], ...]], tuple[float, Any]] = {}


class MercadoError(Exception):
    """Falha ao consultar dados de mercado. A mensagem pode ir direto pro usuário."""


async def buscar_json(
    alvo: str, url: str, params: dict[str, str] | None = None, ttl_s: int = 60
) -> Any:
    chave = (url, tuple(sorted((params or {}).items())))
    agora = time.monotonic()

    if (entrada := _cache.get(chave)) and entrada[0] > agora:
        return entrada[1]

    try:
        with medir_externo(alvo):
            async with httpx.AsyncClient(
                timeout=settings.mercado.timeout_s, headers={"User-Agent": _USER_AGENT}
            ) as client:
                resposta = await client.get(url, params=params)
                resposta.raise_for_status()
                dados = resposta.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise MercadoError("Não encontrei esse dado (moeda ou período inválido).") from e
        raise MercadoError(f"O serviço de cotações ({alvo}) está indisponível agora.") from e
    except (httpx.HTTPError, ValueError) as e:  # ValueError: corpo não é JSON (o BCB devolve HTML ao recusar)
        raise MercadoError(f"O serviço de cotações ({alvo}) está indisponível agora.") from e

    if len(_cache) >= _MAX_ENTRADAS:
        _cache.pop(next(iter(_cache)))
    _cache[chave] = (agora + ttl_s, dados)

    return dados


__all__ = ["MercadoError", "buscar_json"]

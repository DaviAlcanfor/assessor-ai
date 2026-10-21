"""
Base dos clientes das APIs públicas de mercado: GET JSON com cache e métrica por alvo.

O `httpx.AsyncClient` é aberto por chamada (como no cliente do JeV): não há estado de conexão pra
fechar no lifespan, e o cache absorve a repetição. `MercadoError` carrega mensagem segura pro
LLM/usuário — nunca a URL.
"""

from collections.abc import Mapping
from typing import ClassVar

import httpx

from app.domain.errors import ServicoExternoIndisponivel
from app.infra.mercado.cache import CacheTTL, Json
from app.settings import settings
from app.telemetry import medir_externo

# O WAF do BCB recusa o User-Agent padrão do httpx/curl quando as chamadas vêm em rajada.
_USER_AGENT = "assessor-ai/0.1"


class MercadoError(ServicoExternoIndisponivel):
    """Falha ao consultar dados de mercado. A mensagem pode ir direto pro usuário."""


class MercadoClient:
    """Cada subclasse é uma API (`alvo` é o label da métrica) e expõe métodos de negócio tipados;
    quem monta a URL e valida o formato da resposta é ela, via `_url`, `_objeto` e `_lista`."""

    alvo: ClassVar[str]

    def __init__(self, base_url: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._cache = CacheTTL()

    def _url(self, caminho: str, params: Mapping[str, str] | None = None, query_crua: str = "") -> httpx.URL:
        """`params` é codificado pelo httpx. `query_crua` vai como está: o OData do BCB não aceita
        `$format` codificado como `%24format` (ver .agents/skills/mercado.md)."""

        url = httpx.URL(f"{self._base_url}/{caminho.lstrip('/')}", params=params)
        return url.copy_with(query=query_crua.encode()) if query_crua else url

    async def _objeto(self, url: httpx.URL, ttl_s: float) -> dict[str, Json]:
        corpo = await self._get_json(url, ttl_s)
        if not isinstance(corpo, dict):
            raise MercadoError(f"O serviço de cotações ({self.alvo}) respondeu num formato inesperado.")
        return corpo

    async def _lista(self, url: httpx.URL, ttl_s: float) -> list[Json]:
        corpo = await self._get_json(url, ttl_s)
        if not isinstance(corpo, list):
            raise MercadoError(f"O serviço de cotações ({self.alvo}) respondeu num formato inesperado.")
        return corpo

    async def _get_json(self, url: httpx.URL, ttl_s: float) -> Json:
        if (cacheado := self._cache.get(str(url))) is not None:
            return cacheado

        indisponivel = MercadoError(f"O serviço de cotações ({self.alvo}) está indisponível agora.")
        try:
            with medir_externo(self.alvo):
                async with httpx.AsyncClient(
                    timeout=settings.mercado.timeout_s, headers={"User-Agent": _USER_AGENT}
                ) as http:
                    resposta = await http.get(url)
                    resposta.raise_for_status()
                    corpo: Json = resposta.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise MercadoError("Não encontrei esse dado (moeda ou período inválido).") from e
            raise indisponivel from e
        except (httpx.HTTPError, ValueError) as e:  # ValueError: corpo não é JSON (o BCB devolve HTML ao recusar)
            raise indisponivel from e

        self._cache.set(str(url), corpo, ttl_s)
        return corpo

import time
from typing import NamedTuple

# Corpo de uma resposta JSON. Recursivo de propósito: dict/list aninhados até os escalares.
type Json = dict[str, Json] | list[Json] | str | int | float | bool | None


class _Entrada(NamedTuple):
    expira_em: float  # relógio monotônico, em segundos
    valor: Json


class CacheTTL:
    """Cache em memória de respostas JSON, indexado pela URL completa (com a query).

    `get` devolve None tanto pra ausente quanto pra expirado — as APIs de mercado nunca respondem
    `null` no corpo, então não há ambiguidade.

    ponytail: por processo e FIFO — com várias instâncias cada uma cacheia a sua; vira Redis
    (infra/redis.py) se a cota da AwesomeAPI apertar.
    """

    def __init__(self, max_entradas: int = 128) -> None:
        self._max_entradas = max_entradas
        self._entradas: dict[str, _Entrada] = {}

    def get(self, chave: str) -> Json:
        entrada = self._entradas.get(chave)
        if entrada is None or entrada.expira_em <= time.monotonic():
            return None
        return entrada.valor

    def set(self, chave: str, valor: Json, ttl_s: float) -> None:
        if len(self._entradas) >= self._max_entradas:
            self._entradas.pop(next(iter(self._entradas)))  # a mais antiga: dict preserva a inserção
        self._entradas[chave] = _Entrada(expira_em=time.monotonic() + ttl_s, valor=valor)

    def clear(self) -> None:
        self._entradas.clear()

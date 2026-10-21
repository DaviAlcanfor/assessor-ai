"""Métricas HTTP (contagem, duração e requests ativos), por template de rota."""

import time
from collections.abc import Awaitable, Callable

from fastapi import Request
from fastapi.responses import Response

from app.telemetry.metrics import ACTIVE_REQUESTS, HTTP_DURATION, HTTP_REQUESTS

type CallNext = Callable[[Request], Awaitable[Response]]


def _route_template(request: Request) -> str:
    route = request.scope.get("route")
    path = getattr(route, "path", None)
    return path if isinstance(path, str) else "unmatched"


async def observar_http(request: Request, call_next: CallNext) -> Response:
    # A coleta do próprio Prometheus não deve virar métrica de si mesma.
    if request.url.path.startswith("/metrics"):
        return await call_next(request)

    inicio = time.perf_counter()
    status_code = 500
    ACTIVE_REQUESTS.inc()

    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        duracao = time.perf_counter() - inicio
        rota = _route_template(request)
        status_class = f"{status_code // 100}xx"

        ACTIVE_REQUESTS.dec()
        HTTP_REQUESTS.labels(method=request.method, route=rota, status_class=status_class).inc()
        HTTP_DURATION.labels(method=request.method, route=rota).observe(duracao)


__all__ = ["observar_http"]

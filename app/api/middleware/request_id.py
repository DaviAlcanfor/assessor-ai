"""Propaga o `X-Request-ID`: o do cliente (se for sensato) ou um novo, em cada linha de log do request e
no header da resposta — dá pra seguir um request da borda até o log do LLM."""

import re
from collections.abc import Awaitable, Callable
from uuid import uuid4

from fastapi import Request
from fastapi.responses import Response

from app.infra.logging import request_id_var

type CallNext = Callable[[Request], Awaitable[Response]]

# Valor que o cliente controla vai parar em log: só um formato curto e sem quebra de linha.
_REQUEST_ID_VALIDO = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


async def propagar_request_id(request: Request, call_next: CallNext) -> Response:
    recebido = request.headers.get("X-Request-ID")
    request_id = recebido if recebido and _REQUEST_ID_VALIDO.match(recebido) else uuid4().hex[:12]

    token = request_id_var.set(request_id)
    try:
        response = await call_next(request)
    finally:
        request_id_var.reset(token)

    response.headers["X-Request-ID"] = request_id
    return response


__all__ = ["propagar_request_id"]

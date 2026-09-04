"""
Tradução dos erros de domínio (`chat/exceptions.py`) para HTTP.

Fica registrado na app, e não em `try/except` por rota, porque as regras são as mesmas em todas
elas — e porque o handler genérico de `Exception` no fim é a rede que garante que nenhuma rota
devolva stack trace pro cliente, incluindo as que ninguém lembrou de proteger.
"""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from assessor_ai.logging import get_logger
from assessor_ai.schemas.errors import ErrorCode, ErrorResponse
from assessor_ai.services.exceptions import (
    ChatDeOutroUsuario,
    ChatError,
    ChatNaoEncontrado,
    FalhaNoAgente,
    LimiteDeMensagensExcedido,
)

logger = get_logger(__name__)

# (exceção, status HTTP, code do ErrorResponse) — a mensagem vem do `str(exc)` do domínio,
# que é escrita pra ser lida pelo usuário final.
_MAPA: list[tuple[type[ChatError], int, ErrorCode]] = [
    (ChatNaoEncontrado,         status.HTTP_404_NOT_FOUND,         ErrorCode.CHAT_NAO_ENCONTRADO),
    (ChatDeOutroUsuario,        status.HTTP_403_FORBIDDEN,         ErrorCode.CHAT_DE_OUTRO_USUARIO),
    (LimiteDeMensagensExcedido, status.HTTP_429_TOO_MANY_REQUESTS, ErrorCode.LIMITE_DE_MENSAGENS),
    (FalhaNoAgente,             status.HTTP_502_BAD_GATEWAY,       ErrorCode.FALHA_NO_AGENTE),
]


def _resposta(status_code: int, detail: str, code: ErrorCode) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=ErrorResponse(detail=detail, code=code).model_dump(),
    )


def _handler(status_code: int, code: ErrorCode):
    async def handle(request: Request, exc: Exception) -> JSONResponse:
        return _resposta(status_code, str(exc), code)

    return handle


async def _handle_inesperado(request: Request, exc: Exception) -> JSONResponse:
    # Última linha de defesa: loga o traceback real e devolve texto genérico — `str(exc)` de uma
    # exceção não prevista pode carregar query, connection string ou payload.
    logger.exception(f"Erro não tratado em {request.method} {request.url.path}")

    return _resposta(
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        "Erro interno inesperado.",
        ErrorCode.ERRO_INTERNO,
    )


def register_exception_handlers(app: FastAPI) -> None:
    for excecao, status_code, code in _MAPA:
        app.add_exception_handler(excecao, _handler(status_code, code))

    # `ChatError` cobre subclasse nova que ninguém mapeou ainda; `Exception`, o resto do mundo.
    app.add_exception_handler(
        ChatError, _handler(status.HTTP_502_BAD_GATEWAY, ErrorCode.ERRO_NO_CHAT)
    )
    app.add_exception_handler(Exception, _handle_inesperado)


__all__ = ["register_exception_handlers"]

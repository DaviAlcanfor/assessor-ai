"""
Tradução dos erros de domínio (`domain/errors.py`) para HTTP.

Fica registrado na app, e não em `try/except` por rota, porque as regras são as mesmas em todas
elas — e porque o handler genérico de `Exception` no fim é a rede que garante que nenhuma rota
devolva stack trace pro cliente, incluindo as que ninguém lembrou de proteger.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.domain.errors import DomainError, ErrorCode
from app.infra.logging import Logging
from app.schemas.errors import ErrorResponse

logger = Logging.get_logger(__name__)


def _resposta(status_code: int, detail: str, code: ErrorCode) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=ErrorResponse(detail=detail, code=code).model_dump(),
    )


async def _handle_dominio(request: Request, exc: Exception) -> JSONResponse:
    # `str(exc)` é a mensagem interna (vai pro log); pro cliente só `public_message`.
    assert isinstance(exc, DomainError)
    logger.warning("%s em %s %s: %s", type(exc).__name__, request.method, request.url.path, exc)

    return _resposta(exc.status_code, exc.public_message, exc.code)


async def _handle_inesperado(request: Request, exc: Exception) -> JSONResponse:
    # Última linha de defesa: loga o traceback real e devolve texto genérico — `str(exc)` de uma
    # exceção não prevista pode carregar query, connection string ou payload.
    logger.exception(f"Erro não tratado em {request.method} {request.url.path}")

    return _resposta(500, "Erro interno inesperado.", ErrorCode.ERRO_INTERNO)


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(DomainError, _handle_dominio)
    app.add_exception_handler(Exception, _handle_inesperado)


__all__ = ["register_exception_handlers"]

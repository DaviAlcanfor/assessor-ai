"""Decorators que logam a chamada e o resultado das tools do LLM (com PII redigida)."""

import functools
import inspect
import time
from collections.abc import Callable
from enum import StrEnum
from typing import Any

from app.domain.privacy import anonimizar_entrada
from app.infra.logging.setup import DebugLevel, get_logger


class LogType(StrEnum):
    """Categoria da tool, só pra organizar o log: inferida do nome do método (`_tipo_do_metodo`)
    em vez de cada tool inventar na mão o prefixo (`"QUERY OK | ..."`, `"INSERT OK | ..."`)."""

    QUERY    = "QUERY"
    MATCH    = "MATCH"
    INSERT   = "INSERT"
    UPDATE   = "UPDATE"
    DELETE   = "DELETE"
    GENERATE = "GENERATE"
    TOOL     = "TOOL"  # fallback quando o nome não bate com nenhum prefixo conhecido


_PREFIXOS_POR_TIPO: dict[LogType, tuple[str, ...]] = {
    LogType.QUERY:    ("get", "list", "query", "consultar", "buscar", "faq", "cotacao", "ptax", "indicador", "converter", "simular", "total", "daily"),
    LogType.MATCH:    ("match", "find"),
    LogType.INSERT:   ("add", "create", "criar", "adicionar", "definir"),
    LogType.UPDATE:   ("update", "atualizar", "mark", "marcar"),
    LogType.DELETE:   ("discard", "descartar", "remover", "remove", "delete"),
    LogType.GENERATE: ("gerar", "generate"),
}


def _tipo_do_metodo(nome: str) -> LogType:
    for tipo, prefixos in _PREFIXOS_POR_TIPO.items():
        if nome.startswith(prefixos):
            return tipo
    return LogType.TOOL


def _redigir(valor: object) -> str:
    """Anonimiza antes de logar: argumento e resultado de tool carregam texto do usuário."""

    texto, _ = anonimizar_entrada(str(valor))
    return texto


def log_tool[**P, R](
    func: Callable[P, R] | None = None, *, level: DebugLevel = DebugLevel.INFO, metodo: bool = False
) -> Any:
    """Loga chamada/resultado de uma tool. Usável como `@log_tool` ou `@log_tool(level=...)` pra baixar
    o nível das mensagens de rotina (erro sempre sai em ERROR). `metodo=True` esconde o `self`."""

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        logger = get_logger("tools")
        log_rotina = getattr(logger, DebugLevel(level).value.lower())
        tipo = _tipo_do_metodo(func.__name__)

        def antes(args: tuple[object, ...], kwargs: dict[str, object]) -> float:
            visiveis = args[1:] if metodo else args
            log_rotina(
                "%-8s CHAMANDO | %s | args=%s kwargs=%s",
                tipo, func.__name__, _redigir(visiveis), _redigir(kwargs),
            )
            return time.perf_counter()

        def depois(resultado: object, inicio: float) -> None:
            elapsed = time.perf_counter() - inicio
            status = resultado.get("status", "unknown") if isinstance(resultado, dict) else "unknown"
            if status == "error":
                logger.error(
                    "%-8s ERRO     | %s | elapsed=%.3fs | result=%s",
                    tipo, func.__name__, elapsed, _redigir(resultado),
                )
            else:
                log_rotina(
                    "%-8s OK       | %s | elapsed=%.3fs | result=%s",
                    tipo, func.__name__, elapsed, _redigir(resultado),
                )

        if inspect.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> Any:
                inicio = antes(args, kwargs)
                resultado = await func(*args, **kwargs)
                depois(resultado, inicio)
                return resultado

            return async_wrapper  # type: ignore[return-value]

        @functools.wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            inicio = antes(args, kwargs)
            resultado = func(*args, **kwargs)
            depois(resultado, inicio)
            return resultado

        return sync_wrapper

    return decorator(func) if func is not None else decorator


def log_classe(
    cls_alvo: type | None = None,
    *,
    level: DebugLevel = DebugLevel.INFO,
    ignore: frozenset[str] = frozenset(),
) -> Any:
    """Aplica `log_tool` em todo método público da classe. Usável como `@log_classe` ou
    `@log_classe(level=DebugLevel.DEBUG)`.

    `ignore` tira métodos que não são "chamadas de tool" de verdade — em `ToolSet`, por exemplo,
    `as_tools()` só monta a lista pro LangChain, não deveria logar "CHAMANDO | as_tools" toda vez
    que o grafo monta o agente."""

    def decorator(cls_alvo: type) -> type:
        for nome, atributo in list(vars(cls_alvo).items()):
            if nome.startswith("_") or nome in ignore or not inspect.isfunction(atributo):
                continue
            setattr(cls_alvo, nome, log_tool(atributo, level=level, metodo=True))
        return cls_alvo

    return decorator(cls_alvo) if cls_alvo is not None else decorator


__all__ = ["LogType", "log_classe", "log_tool"]

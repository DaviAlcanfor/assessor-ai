import functools
import logging
import time
from collections.abc import Callable
from enum import StrEnum

from assessor_ai.privacy import anonimizar_entrada


class Colors(StrEnum):
    GREEN  = "\033[92m"
    RED    = "\033[91m"
    YELLOW = "\033[93m"
    WHITE  = "\033[97m"
    RESET  = "\033[0m"


LEVEL_COLORS = {
    "DEBUG":    Colors.WHITE,
    "INFO":     Colors.GREEN,
    "WARNING":  Colors.YELLOW,
    "ERROR":    Colors.RED,
    "CRITICAL": Colors.RED,
}


def _injetar_cor(record: logging.LogRecord) -> bool:
    record.color = LEVEL_COLORS.get(record.levelname, Colors.WHITE)
    record.reset = Colors.RESET
    return True


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.addFilter(_injetar_cor)
        handler.setFormatter(logging.Formatter("%(color)s%(levelname)s | %(name)s | %(message)s%(reset)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

    return logger


_tool_logger = get_logger("pg_tools")


def _redigir(valor: object) -> str:
    texto, _ = anonimizar_entrada(str(valor))
    return texto


def log_tool[**P, R](func: Callable[P, R]) -> Callable[P, R]:

    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:

        _tool_logger.info("CHAMANDO | %s | args=%s kwargs=%s", func.__name__, _redigir(args), _redigir(kwargs))

        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start

        if not isinstance(result, dict):
            status = "unknown"
        else:
            status = result.get("status", "unknown")

        result_redigido = _redigir(result)

        match status:
            case "error":
                _tool_logger.error("ERRO     | %s | elapsed=%.3fs | result=%s", func.__name__, elapsed, result_redigido)

            case _:
                _tool_logger.info("OK       | %s | elapsed=%.3fs | result=%s", func.__name__, elapsed, result_redigido)

        return result

    return wrapper


__all__ = ["get_logger", "log_tool"]

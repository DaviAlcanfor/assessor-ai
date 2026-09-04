import asyncio
import sys
import warnings

import uvicorn
from langchain_core._api.deprecation import LangChainPendingDeprecationWarning

warnings.filterwarnings(
    "ignore",
    category=LangChainPendingDeprecationWarning,
    message=r".*allowed_objects.*",
)

from assessor_ai.tui import app as tui_app

if sys.platform == "win32":
    # O checkpointer do grafo usa psycopg3 async, que recusa o ProactorEventLoop (padrão do
    # asyncio no Windows) — o pool não consegue abrir conexão e todo turno morre num PoolTimeout
    # de 30s. Vale pra TUI e pra API: as duas caem no mesmo pool.
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def run_api() -> None:
    uvicorn.run(
        "assessor_ai.api.app:app",
        host="0.0.0.0", 
        port=8000, 
        reload=True
    )


OPTIONS = {
    "tui": tui_app.run,
    "api": run_api,
}


def print_usage() -> None:
    print("Uso:")
    print("  python main.py tui")
    print("  python main.py api")


def main() -> None:
    args = sys.argv[1:]

    if len(args) != 1:
        print_usage()
        sys.exit(1)

    mode = args[0]
    handler = OPTIONS.get(mode)

    if handler is None:
        print(f"Modo inválido: {mode}\n")
        print_usage()
        sys.exit(1)

    handler()


if __name__ == "__main__":
    main()

import sys
import warnings

from langchain_core._api.deprecation import LangChainPendingDeprecationWarning

# langgraph-checkpoint 4.0.2 instancia `Reviver()` sem `allowed_objects` ao ser
# importado, disparando esse warning só por causa da import — não é algo que
# nosso código controla. Suprime até a lib fixar isso ou atualizarmos a versão.
warnings.filterwarnings(
    "ignore",
    category=LangChainPendingDeprecationWarning,
    message=r".*allowed_objects.*",
)

from interfaces.terminal import app


def run_tui() -> None:
    print("TUI ainda não implementada — ver TODO.md.")
    sys.exit(1)


def run_api() -> None:
    print("API ainda não implementada — ver TODO.md.")
    sys.exit(1)


OPTIONS = {
    "terminal": app.run,
    "tui":      run_tui,
    "api":      run_api,
}


def print_usage() -> None:
    print("Uso:")
    print("  python main.py terminal")
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

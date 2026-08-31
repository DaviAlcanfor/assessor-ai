import pyfiglet
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()

# Paleta do design system da Kobana (mesma de web/src/styles/tokens.css):
# lime = assistente, purple = usuário, gray = neutro/logs.
LIME = "#d3fd54"
PURPLE = "#a630da"


def exibir_titulo() -> None:

    ascii_art = pyfiglet.figlet_format("ASSESSOR.AI", font="doom")
    console.print(f"[{LIME}]{ascii_art}[/{LIME}]")
    console.print("[dim]Digite '/exit' para sair.[/dim]\n")


def exibir_usuario(mensagem: str) -> None:

    console.print(Panel(
        Text(mensagem, style="white"),
        title=f"[bold {PURPLE}]Você[/bold {PURPLE}]",
        title_align="left",
        border_style=PURPLE,
    ))


def exibir_assistente(mensagem: str) -> None:

    console.print(Panel(
        Text(mensagem, style="white"),
        title=f"[bold {LIME}]Assessor[/bold {LIME}]",
        title_align="left",
        border_style=LIME,
    ))
    

__all__ = [
    "LIME",
    "PURPLE",
    "console",
    "exibir_assistente",
    "exibir_titulo",
    "exibir_usuario"
]

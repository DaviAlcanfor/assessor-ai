from rich.panel import Panel
from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import LoadingIndicator, Static

# Paleta do design system da Kobana (mesma de web/src/styles/tokens.css):
# lime = assistente, purple = usuário.
_ESTILO = {
    "usuario": ("Você", "#a630da"),
    "assistente": ("Assessor", "#d3fd54"),
}


class Bubble(Static):
    """Uma mensagem no histórico do chat, no mesmo estilo de Panel do terminal."""

    def __init__(self, texto: str, tipo: str) -> None:
        titulo, cor = _ESTILO[tipo]
        painel = Panel(
            Text(texto, style="white"),
            title=f"[bold {cor}]{titulo}[/bold {cor}]",
            title_align="left",
            border_style=cor,
        )
        super().__init__(painel, classes=tipo)


class MessageRow(Horizontal):
    """Linha que alinha uma Bubble à direita (usuário) ou à esquerda (assistente)."""


class Pensando(Horizontal):
    """Indicador de carregamento (bolinhas) enquanto o assistente responde."""

    def compose(self) -> ComposeResult:
        yield LoadingIndicator()


__all__ = ["Bubble", "MessageRow", "Pensando"]

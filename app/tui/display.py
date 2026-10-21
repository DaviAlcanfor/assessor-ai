from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import LoadingIndicator, Static


class Bubble(Static):
    """
    Uma mensagem no histórico do chat: bolha preenchida, cor por papel (lime = assistente,
    purple = usuário), igual ao `MessageBubble` do web. Cor e padding vivem no `app.tcss`.
    """

    def __init__(self, texto: str, tipo: str) -> None:
        # `Text` em vez de str cru: o conteúdo vem do usuário e do LLM, e colchete solto
        # seria interpretado como markup do Textual.
        super().__init__(Text(texto), classes=tipo)


class MessageRow(Horizontal):
    """Linha que alinha uma Bubble à direita (usuário) ou à esquerda (assistente)."""


class Pensando(Horizontal):
    """Indicador de carregamento enquanto o assistente responde."""

    def compose(self) -> ComposeResult:
        yield LoadingIndicator()


__all__ = ["Bubble", "MessageRow", "Pensando"]

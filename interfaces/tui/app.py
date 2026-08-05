from assessor_ai.chat import service
from textual import work
from textual.app import App, ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Footer, Header, Input

from interfaces.tui.display import PENSANDO, Bubble


class AssessorTUI(App):
    CSS_PATH = "app.tcss"
    BINDINGS = [("ctrl+c", "sair", "Sair")]


    def __init__(self) -> None:
        super().__init__()
        self.user_id = ""
        self.session_id = ""


    def compose(self) -> ComposeResult:
        yield Header(name="Assessor.AI")
        yield VerticalScroll(id="historico")
        yield Input(placeholder="Digite sua mensagem... (/exit para sair)")
        yield Footer()


    def on_mount(self) -> None:
        self.user_id, self.session_id = service.iniciar_sessao()


    async def on_input_submitted(self, evento: Input.Submitted) -> None:
        texto = evento.value.strip()
        evento.input.clear()

        if not texto:
            return

        if texto == "/exit":
            await self.action_sair()
            return

        await self._enviar(texto)


    async def _enviar(self, texto: str) -> None:
        historico = self.query_one("#historico", VerticalScroll)
        input_widget = self.query_one(Input)

        await historico.mount(Bubble(f"Você: {texto}", classes="usuario"))
        indicador = Bubble(PENSANDO, classes="pensando")
        await historico.mount(indicador)
        historico.scroll_end(animate=False)

        input_widget.disabled = True
        self._processar(texto, indicador)


    @work(thread=True)
    def _processar(self, texto: str, indicador: Bubble) -> None:
        try:
            resposta = service.send_message(self.user_id, self.session_id, texto)
        except Exception as e:
            resposta = f"Erro: {e}"

        self.call_from_thread(self._exibir_resposta, indicador, resposta)


    def _exibir_resposta(self, indicador: Bubble, resposta: str) -> None:
        indicador.remove_class("pensando")
        indicador.add_class("assistente")
        indicador.update(f"Assessor: {resposta}")

        self.query_one("#historico", VerticalScroll).scroll_end(animate=False)
        input_widget = self.query_one(Input)
        input_widget.disabled = False
        input_widget.focus()


    async def action_sair(self) -> None:
        if self.session_id:
            service.encerrar_sessao(self.session_id, self.user_id)
        self.exit()


def run() -> None:
    AssessorTUI().run()


__all__ = ["AssessorTUI", "run"]

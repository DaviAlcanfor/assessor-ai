from assessor_ai.chat import service
from interfaces.terminal.display import (
    console,
    exibir_assistente,
    exibir_titulo,
    exibir_usuario,
)


def run() -> None:
    exibir_titulo()

    user_id, session_id = service.iniciar_sessao()

    while True:
        try:
            user_input = console.input("[bold green]>[/bold green] ").strip()

            if user_input == "/exit":
                service.encerrar_sessao(session_id, user_id)
                console.print("\n[dim]Encerrando...[/dim]")
                break

            if not user_input:
                continue

            exibir_usuario(user_input)
            resposta = service.send_message(user_id, session_id, user_input)
            exibir_assistente(resposta)

        except KeyboardInterrupt:
            service.encerrar_sessao(session_id, user_id)
            console.print("\n[dim]Encerrando...[/dim]")
            break
        except Exception as e:
            console.print(f"[bold red]Erro:[/bold red] {e}")


__all__ = ["run"]

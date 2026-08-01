import os
from uuid import uuid4

from chat import service
from config.docker import garantir_banco
from interfaces.terminal.display import (
    console,
    exibir_assistente,
    exibir_titulo,
    exibir_usuario,
)


def run() -> None:
    os.system("cls")

    garantir_banco()
    exibir_titulo()

    user_id = str(uuid4())
    session_id = service.create_chat(user_id)

    # mock pra teste
    service.garantir_usuario(
        user_id,
        nome="USUARIO FALSO PARA TESTE",
        email="TESTE@TESTE.com"
    )

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

from uuid import uuid4

from assessor_ai.chat import service
from config.docker import garantir_ambiente
from interfaces.terminal.display import (
    console,
    exibir_assistente,
    exibir_titulo,
    exibir_usuario,
)
from mocks.generate_user import generate_user


def run(local: bool = False) -> None:
    if local:
        garantir_ambiente()

    exibir_titulo()

    usuario_existente = service.buscar_usuario_existente()
    
    if usuario_existente:
        user_id = usuario_existente["user_id"]
    
    else:
        user_id = str(uuid4())
        novo_usuario = generate_user()
    
        service.garantir_usuario(
            user_id,
            nome=novo_usuario["name"],
            email=novo_usuario["email"]
        )

    session_id = service.create_chat(user_id)

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

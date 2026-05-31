from langchain_core.messages import AIMessage
from uuid import uuid4
from graph.builder import fluxo_agentes
from ui.terminal import (
    exibir_titulo,
    exibir_usuario,
    exibir_assistente, 
    console,
)


def executar_fluxo_assessor(
    pergunta_usuario: str, 
    session_id: str
) -> str:

    estado_inicial = {
        "messages":         [{"role": "human", "content": pergunta_usuario}],
        "agentes_chamados": [],
    }

    estado_final = fluxo_agentes.invoke(
        estado_inicial,
        config={"configurable": {"thread_id": session_id}},
    )

    for msg in reversed(estado_final.get("messages", [])):
        if isinstance(msg, AIMessage):
            return msg.content

    return "Sem resposta."


def main() -> None:

    exibir_titulo()
    session_id = str(uuid4())
    
    while True:
        try:
            user_input = console.input("[bold green]>[/bold green] ").strip()

            if user_input == "/exit":
                console.print("\n[dim]Encerrando...[/dim]")
                break

            if not user_input:
                continue

            exibir_usuario(user_input)
            resposta = executar_fluxo_assessor(user_input, session_id=session_id)
            exibir_assistente(resposta)

        except KeyboardInterrupt:
            console.print("\n[dim]Encerrando...[/dim]")
            break
        except Exception as e:
            console.print(f"[bold red]Erro:[/bold red] {e}")


if __name__ == "__main__":
    main()
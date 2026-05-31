from langchain_core.messages import AIMessage
from langchain_core.messages import messages_to_dict, messages_from_dict
from uuid import uuid4
import os

from graph.builder import fluxo_agentes
from config.docker import garantir_banco
from tools.mongo.core import (
    inserir,
    buscar,
    atualizar
)
from ui.terminal import (
    exibir_titulo,
    exibir_usuario,
    exibir_assistente, 
    console,
)


def montar_mensagem_humana(conteudo: str) -> dict:
    return {"role": "human", "content": conteudo}


def executar_fluxo_assessor(
    pergunta_usuario: str, 
    session_id: str
) -> str:
    
    historico = buscar(session_id)
    nova_msg = montar_mensagem_humana(pergunta_usuario)
    historico_msg = messages_from_dict(historico["messages"]) if historico else []
    
    estado_inicial = {
        "messages": historico_msg + [nova_msg],
        "agentes_chamados": [],
    }

    estado_final = fluxo_agentes.invoke(
        estado_inicial,
        config={"configurable": {"thread_id": session_id}},
    )

    messages = messages_to_dict(estado_final["messages"])
    
    if not historico:
        inserir(session_id, messages=messages)
    else:
        atualizar(session_id, messages=messages)
    

    for msg in estado_final["messages"][::-1]:
        if isinstance(msg, AIMessage):
            return msg.content

    return "Sem resposta."


def main() -> None:
    os.system("cls")
    
    garantir_banco()
    exibir_titulo()
    session_id = "session_1"    
    
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
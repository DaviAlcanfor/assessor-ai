from langchain_core.messages import AIMessage
from uuid import uuid4
import os

from graph.builder import fluxo_agentes
from config.docker import garantir_banco
from tools.mongo.core import (
    inserir,
    buscar,
    adicionar_mensagens,
    encerrar_sessao,
)
from tools.mongo.schemas import Mensagem
from ui.terminal import (
    exibir_titulo,
    exibir_usuario,
    exibir_assistente,
    console,
)


# --------------------- FIX WARNING ---------------------
import logging
import warnings

warnings.filterwarnings("ignore", message="Deserializing unregistered type")
logging.getLogger("langgraph").setLevel(logging.ERROR)
# --------------------- FIX WARNING ---------------------


def montar_mensagem_humana(conteudo: str) -> Mensagem:
    return Mensagem(role="human", content=conteudo)


def executar_fluxo_assessor(
    pergunta_usuario: str,
    session_id: str,
    user_id: str,
) -> str:
    
    historico = buscar(session_id)
    nova_msg = montar_mensagem_humana(pergunta_usuario)
    historico_msgs = Mensagem.de_dict(historico["messages"]) if historico else []

    estado_inicial = {
        "messages": [m.para_langchain() for m in historico_msgs] + [nova_msg.para_langchain()],
        "agentes_chamados": [],
    }

    estado_final = fluxo_agentes.invoke(
        estado_inicial,
        config={"configurable": {"thread_id": session_id}},
    )

    if not estado_final.get("mensagem_bloqueada"):
        todas = Mensagem.de_langchain(estado_final["messages"])
        novas = todas[len(historico_msgs):]

        if not historico:
            inserir(user_id, session_id, novas)
        else:
            adicionar_mensagens(session_id, novas)

    for msg in estado_final["messages"][::-1]:
        if isinstance(msg, AIMessage):
            return msg.content

    return "Sem resposta."


def main() -> None:
    os.system("cls")
    
    garantir_banco()
    exibir_titulo()
    user_id = "dev"  
    session_id = str(uuid4())

    while True:
        try:
            user_input = console.input("[bold green]>[/bold green] ").strip()

            if user_input == "/exit":
                encerrar_sessao(session_id)
                console.print("\n[dim]Encerrando...[/dim]")
                break

            if not user_input:
                continue

            exibir_usuario(user_input)
            resposta = executar_fluxo_assessor(user_input, session_id=session_id, user_id=user_id)
            exibir_assistente(resposta)

        except KeyboardInterrupt:
            console.print("\n[dim]Encerrando...[/dim]")
            break
        except Exception as e:
            console.print(f"[bold red]Erro:[/bold red] {e}")


if __name__ == "__main__":
    main()
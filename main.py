from langchain_core.messages import AIMessage
from uuid import uuid4
import os

from graph.builder import fluxo_agentes
from config.docker import garantir_banco
import tools.mongo.chats.core as chats
import tools.mongo.users.core as users
from tools.mongo.chats.schemas import Mensagem, Role

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
    return Mensagem(
        role=Role.HUMAN, 
        content=conteudo
    )


def salvar_mensagens(user_id: str, session_id: str, mensagens: list[Mensagem]) -> None:
    if not chats.buscar(session_id):
        chats.criar(user_id, session_id, mensagens)
    else:
        chats.atualizar_mensagens(session_id, mensagens)
        
def _extrair_resposta(estado_final: dict) -> str | None:
    for msg in estado_final["messages"][::-1]:
        if isinstance(msg, AIMessage):
            return msg.content
    return None
        

def executar_fluxo_assessor(
    pergunta_usuario: str,
    session_id: str,
    user_id: str,
) -> str:
    
    nova_msg = montar_mensagem_humana(pergunta_usuario)
    usuario  = users.buscar(user_id)
    perfil   = usuario.get("profile", "") if usuario else ""

    estado_inicial = {
        "messages":         [nova_msg.para_langchain()],
        "agentes_chamados": [],
        "perfil_usuario":   perfil,
    }

    estado_final = fluxo_agentes.invoke(
        estado_inicial,
        config={"configurable": {"thread_id": session_id}},
    )

    resposta = _extrair_resposta(estado_final)

    if not resposta:
        return "Sem resposta."

    novas = [nova_msg, Mensagem(role=Role.AI, content=resposta)]
    salvar_mensagens(user_id, session_id, novas)

    return resposta


def main() -> None:
    os.system("cls")
    
    garantir_banco()
    exibir_titulo()
    user_id = str(uuid4())   
    session_id = str(uuid4())
    
    # mock pra teste
    users.garantir_usuario(
        user_id,
        nome="USUARIO FALSO PARA TESTE", 
        email="TESTE@TESTE.com"
    )
    

    while True:
        try:
            user_input = console.input("[bold green]>[/bold green] ").strip()

            if user_input == "/exit":
                chats.encerrar_sessao(session_id, user_id)
                console.print("\n[dim]Encerrando...[/dim]")
                break

            if not user_input:
                continue

            exibir_usuario(user_input)
            resposta = executar_fluxo_assessor(user_input, session_id=session_id, user_id=user_id)
            exibir_assistente(resposta)

        except KeyboardInterrupt:
            chats.encerrar_sessao(session_id, user_id)
            console.print("\n[dim]Encerrando...[/dim]")
            break
        except Exception as e:
            console.print(f"[bold red]Erro:[/bold red] {e}")


if __name__ == "__main__":
    main()
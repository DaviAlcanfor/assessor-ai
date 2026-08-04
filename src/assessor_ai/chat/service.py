from uuid import uuid4

from assessor_ai.agents.nodes.guardrail.entrada import anonimizar_entrada
from assessor_ai.chat import repositories, runner
from assessor_ai.chat.models import ChatMessage, Role


def create_chat(user_id: str) -> str:
    return str(uuid4())


def garantir_usuario(user_id: str, nome: str, email: str) -> None:
    repositories.garantir_usuario(user_id, nome=nome, email=email)


def send_message(user_id: str, session_id: str, content: str) -> str:
    mensagem = ChatMessage(role=Role.HUMAN, content=content)
    perfil = repositories.buscar_perfil(user_id)

    resposta = runner.executar(mensagem, session_id, perfil)

    if not resposta:
        return "Sem resposta."

    conteudo_redigido, _ = anonimizar_entrada(content)
    novas = [
        ChatMessage(role=Role.HUMAN, content=conteudo_redigido), 
        ChatMessage(role=Role.AI, content=resposta)
    ]
    repositories.salvar_mensagens(user_id, session_id, novas)

    return resposta


def get_history(session_id: str) -> list[ChatMessage] | None:
    return repositories.buscar_historico(session_id)


def encerrar_sessao(session_id: str, user_id: str) -> None:
    repositories.encerrar_sessao(session_id, user_id)


__all__ = [
    "create_chat",
    "encerrar_sessao",
    "garantir_usuario",
    "get_history",
    "send_message",
]

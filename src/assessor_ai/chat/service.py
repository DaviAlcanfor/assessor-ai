from uuid import uuid4

from assessor_ai.agents.nodes.guardrail.entrada import anonimizar_entrada
from assessor_ai.chat import repositories, runner
from assessor_ai.chat.models import ChatMessage, Role
from assessor_ai.tools.redis.chat import can_send_message
from mocks.generate_user import generate_user


class LimiteDeMensagensExcedido(Exception):
    pass


def create_chat(user_id: str) -> str:
    session_id = str(uuid4())
    repositories.criar_chat(user_id, session_id)
    return session_id


def obter_dono_chat(session_id: str) -> str | None:
    return repositories.buscar_dono_chat(session_id)


def garantir_usuario(user_id: str, nome: str, email: str) -> None:
    repositories.garantir_usuario(user_id, nome=nome, email=email)


def buscar_usuario_existente() -> dict | None:
    return repositories.buscar_usuario_existente()


def obter_ou_criar_usuario(nome: str, email: str) -> str:
    usuario = repositories.buscar_usuario_por_email(email)
    
    if usuario:
        return usuario["user_id"]

    user_id = str(uuid4())
    garantir_usuario(user_id, nome=nome, email=email)
    
    return user_id


def iniciar_sessao() -> tuple[str, str]:
    usuario_existente = buscar_usuario_existente()

    if usuario_existente:
        user_id = usuario_existente["user_id"]
    else:
        user_id = str(uuid4())
        novo_usuario = generate_user()
        garantir_usuario(
            user_id, 
            nome=novo_usuario["name"],
            email=novo_usuario["email"]
        )

    session_id = create_chat(user_id)

    return user_id, session_id


def send_message(user_id: str, session_id: str, content: str) -> str:
    if not can_send_message(user_id):
        raise LimiteDeMensagensExcedido(
            "Você atingiu o limite de mensagens. Tente novamente em alguns instantes."
        )

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
    "LimiteDeMensagensExcedido",
    "buscar_usuario_existente",
    "create_chat",
    "encerrar_sessao",
    "garantir_usuario",
    "get_history",
    "iniciar_sessao",
    "obter_dono_chat",
    "obter_ou_criar_usuario",
    "send_message",
]

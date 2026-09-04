import asyncio

from faker import Faker

from assessor_ai.api.limiter import can_send_message
from assessor_ai.graph.tools.chats.schemas import ChatRecord
from assessor_ai.graph.tools.usuarios.schemas import UserRecord
from assessor_ai.identifiers import ChatID, UserID, novo_chat_id, novo_user_id
from assessor_ai.privacy import anonimizar_entrada
from assessor_ai.repositories import chat_repository
from assessor_ai.schemas.models import ChatMessage, Role
from assessor_ai.services import runner
from assessor_ai.services.exceptions import (
    ChatDeOutroUsuario,
    ChatNaoEncontrado,
    FalhaNoAgente,
    LimiteDeMensagensExcedido,
)

_fake = Faker()


def _gerar_usuario_mock() -> dict[str, str]:
    return {
        "name": _fake.name(), 
        "email": _fake.email()
    }


async def create_chat(user_id: UserID) -> ChatID:
    session_id = novo_chat_id()
    await chat_repository.criar_chat(user_id, session_id)
    
    return session_id


async def obter_dono_chat(session_id: ChatID) -> UserID | None:
    return await chat_repository.buscar_dono_chat(session_id)


async def validar_ownership(session_id: ChatID, user_id: UserID) -> None:
    """
    Garante que o chat existe e pertence a `user_id`.
    Levanta `ChatNaoEncontrado` ou `ChatDeOutroUsuario` — quem chama decide como apresentar.
    """

    dono = await obter_dono_chat(session_id)

    if dono is None:
        raise ChatNaoEncontrado(session_id)

    if dono != user_id:
        raise ChatDeOutroUsuario(session_id)


async def garantir_usuario(user_id: UserID, nome: str, email: str) -> None:
    await chat_repository.garantir_usuario(user_id, nome=nome, email=email)


async def buscar_usuario_existente() -> UserRecord | None:
    return await chat_repository.buscar_usuario_existente()


async def obter_ou_criar_usuario(nome: str, email: str) -> UserID:
    usuario = await chat_repository.buscar_usuario_por_email(email)

    if usuario:
        return usuario["user_id"]

    user_id = novo_user_id()
    await garantir_usuario(user_id, nome=nome, email=email)

    return user_id


async def listar_usuarios() -> list[UserRecord]:
    return await chat_repository.listar_usuarios()


async def listar_chats(user_id: UserID) -> list[ChatRecord]:
    return await chat_repository.listar_chats(user_id)


async def obter_usuario_padrao() -> UserID:
    """
    Reaproveita o primeiro usuário existente, ou cria um mock — mesmo bootstrap usado por
    TUI (`iniciar_sessao`) e pela auth da API quando `API_KEY_AUTH_ENABLED=false`.
    """

    usuario_existente = await buscar_usuario_existente()

    if usuario_existente:
        return usuario_existente["user_id"]

    user_id = novo_user_id()
    novo_usuario = _gerar_usuario_mock()
    await garantir_usuario(user_id, nome=novo_usuario["name"], email=novo_usuario["email"])

    return user_id


async def iniciar_sessao() -> tuple[UserID, ChatID]:
    user_id = await obter_usuario_padrao()
    session_id = await create_chat(user_id)

    return user_id, session_id


async def send_message(user_id: UserID, session_id: ChatID, content: str) -> str:
    """
    Envia mensagem do usuário para o chat e obtém a resposta do modelo de IA.
    """

    if not await asyncio.to_thread(can_send_message, user_id):
        raise LimiteDeMensagensExcedido(
            "Você atingiu o limite de mensagens. Tente novamente em alguns instantes."
        )

    mensagem = ChatMessage(role=Role.HUMAN, content=content)
    perfil = await chat_repository.buscar_perfil(user_id)

    try:
        resposta = await runner.executar(mensagem, session_id, perfil, user_id)
    except Exception as e:
        raise FalhaNoAgente("Não foi possível processar a mensagem.") from e

    if not resposta:
        return "Sem resposta."

    conteudo_redigido, _ = anonimizar_entrada(content)
    novas = [
        ChatMessage(role=Role.HUMAN, content=conteudo_redigido),
        ChatMessage(role=Role.AI, content=resposta),
    ]
    await chat_repository.salvar_mensagens(user_id, session_id, novas)

    return resposta


async def get_history(session_id: ChatID, user_id: UserID) -> list[ChatMessage] | None:
    return await chat_repository.buscar_historico(session_id, user_id)


async def encerrar_sessao(session_id: ChatID, user_id: UserID) -> None:
    await chat_repository.encerrar_sessao(session_id, user_id)


__all__ = [
    "ChatDeOutroUsuario",
    "ChatNaoEncontrado",
    "FalhaNoAgente",
    "LimiteDeMensagensExcedido",
    "buscar_usuario_existente",
    "create_chat",
    "encerrar_sessao",
    "garantir_usuario",
    "get_history",
    "iniciar_sessao",
    "listar_chats",
    "listar_usuarios",
    "obter_dono_chat",
    "obter_ou_criar_usuario",
    "obter_usuario_padrao",
    "send_message",
    "validar_ownership",
]

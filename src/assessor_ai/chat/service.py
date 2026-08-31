import asyncio
from uuid import uuid4

from faker import Faker

from assessor_ai.agents.nodes.guardrail.entrada import anonimizar_entrada
from assessor_ai.chat import repositories, runner
from assessor_ai.chat.models import ChatMessage, Role
from assessor_ai.tools.redis.chat import can_send_message

_fake = Faker()


class LimiteDeMensagensExcedido(Exception):
    pass


def _gerar_usuario_mock() -> dict:
    return {"name": _fake.name(), "email": _fake.email()}


async def create_chat(user_id: str) -> str:
    session_id = str(uuid4())
    await repositories.criar_chat(user_id, session_id)
    return session_id


async def obter_dono_chat(session_id: str) -> str | None:
    return await repositories.buscar_dono_chat(session_id)


async def garantir_usuario(user_id: str, nome: str, email: str) -> None:
    await repositories.garantir_usuario(user_id, nome=nome, email=email)


async def buscar_usuario_existente() -> dict | None:
    return await repositories.buscar_usuario_existente()


async def obter_ou_criar_usuario(nome: str, email: str) -> str:
    usuario = await repositories.buscar_usuario_por_email(email)

    if usuario:
        return usuario["user_id"]

    user_id = str(uuid4())
    await garantir_usuario(user_id, nome=nome, email=email)

    return user_id


async def listar_usuarios() -> list[dict]:
    return await repositories.listar_usuarios()


async def listar_chats(user_id: str) -> list[dict]:
    return await repositories.listar_chats(user_id)


async def obter_usuario_padrao() -> str:
    """
    Reaproveita o primeiro usuário existente, ou cria um mock — mesmo bootstrap usado por
    TUI (`iniciar_sessao`) e pela auth da API quando `API_KEY_AUTH_ENABLED=false`.
    """

    usuario_existente = await buscar_usuario_existente()

    if usuario_existente:
        return usuario_existente["user_id"]

    user_id = str(uuid4())
    novo_usuario = _gerar_usuario_mock()
    await garantir_usuario(user_id, nome=novo_usuario["name"], email=novo_usuario["email"])

    return user_id


async def iniciar_sessao() -> tuple[str, str]:
    user_id = await obter_usuario_padrao()
    session_id = await create_chat(user_id)

    return user_id, session_id


async def send_message(user_id: str, session_id: str, content: str) -> str:
    """
    Envia mensagem do usuário para o chat e obtém a resposta do modelo de IA.
    """

    if not await asyncio.to_thread(can_send_message, user_id):
        raise LimiteDeMensagensExcedido(
            "Você atingiu o limite de mensagens. Tente novamente em alguns instantes."
        )

    mensagem = ChatMessage(role=Role.HUMAN, content=content)
    perfil = await repositories.buscar_perfil(user_id)

    resposta = await runner.executar(mensagem, session_id, perfil, user_id)

    if not resposta:
        return "Sem resposta."

    conteudo_redigido, _ = anonimizar_entrada(content)
    novas = [
        ChatMessage(role=Role.HUMAN, content=conteudo_redigido),
        ChatMessage(role=Role.AI, content=resposta),
    ]
    await repositories.salvar_mensagens(user_id, session_id, novas)

    return resposta


async def get_history(session_id: str, user_id: str) -> list[ChatMessage] | None:
    return await repositories.buscar_historico(session_id, user_id)


async def encerrar_sessao(session_id: str, user_id: str) -> None:
    await repositories.encerrar_sessao(session_id, user_id)


__all__ = [
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
]

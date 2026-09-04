"""
Chat API routes

Rotas para chat:
- create_chat: cria um novo chat
- send_message: envia uma mensagem para um chat específico
- get_messages: obtém as mensagens de histórico de um chat específico
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from assessor_ai.api.auth import get_current_user
from assessor_ai.api.limiter import limiter
from assessor_ai.graph.tools.chats.schemas import ChatRecord
from assessor_ai.identifiers import ChatID, UserID
from assessor_ai.schemas.chat import (
    ChatCreateResponse,
    ChatMessageResponse,
    ChatSummary,
    MessageCreate,
    MessageResponse,
    Role,
)
from assessor_ai.schemas.models import Role as DomainRole
from assessor_ai.services import chat_service

_ROLE_MAP = {
    DomainRole.HUMAN: Role.USER,
    DomainRole.AI: Role.ASSISTANT,
}


# API Router
# Rota para criar um novo chat e continuar nele
router = APIRouter(prefix="/v1/chats", tags=["chats"])


@router.post("", response_model=ChatCreateResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def create_chat(
    request: Request, user_id: Annotated[UserID, Depends(get_current_user)]
) -> ChatCreateResponse:
    """
    Cria um chat caso não exista de acordo com o usuário autenticado.
    Retorna o chat_id (session_id) do chat criado.
    """

    return ChatCreateResponse(chat_id=await chat_service.create_chat(user_id))


def _titulo(chat: ChatRecord) -> str:
    mensagens = chat.get("messages") or []

    if mensagens and mensagens[0].get("role") == "human":
        conteudo = mensagens[0]["content"]
        return conteudo[:40] + "…" if len(conteudo) > 40 else conteudo

    return "Nova conversa"


@router.get("", response_model=list[ChatSummary])
@limiter.limit("20/minute")
async def list_chats(
    request: Request, user_id: Annotated[UserID, Depends(get_current_user)]
) -> list[ChatSummary]:
    """
    Lista os chats do usuário autenticado, mais recentes primeiro.
    """

    chats = await chat_service.listar_chats(user_id)

    return [
        ChatSummary(
            chat_id=ChatID(c["session_id"]),
            title=_titulo(c),
            updated_at=c["updated_at"],
        )
        for c in chats
    ]


# Rota para enviar uma mensagem para um chat específico
@router.post("/{chat_id}/messages", response_model=ChatMessageResponse)
@limiter.limit("10/minute")
async def send_message(
    request: Request,
    chat_id: str,
    payload: MessageCreate,
    user_id: Annotated[UserID, Depends(get_current_user)],
) -> ChatMessageResponse:
    """
    Envia uma mensagem para um chat específico.
    """

    typed_chat_id = ChatID(chat_id)
    await chat_service.validar_ownership(typed_chat_id, user_id)
    resposta = await chat_service.send_message(user_id, typed_chat_id, payload.content)

    return ChatMessageResponse(chat_id=typed_chat_id, content=resposta)


@router.get("/{chat_id}/messages", response_model=list[MessageResponse])
@limiter.limit("20/minute")
async def get_messages(
    request: Request,
    chat_id: str,
    user_id: Annotated[UserID, Depends(get_current_user)],
) -> list[MessageResponse]:
    """
    Obtém as mensagens de histórico de um chat específico.
    """

    typed_chat_id = ChatID(chat_id)
    await chat_service.validar_ownership(typed_chat_id, user_id)

    historico = await chat_service.get_history(typed_chat_id, user_id) or []

    return [
        MessageResponse(role=_ROLE_MAP[m.role], content=m.content)
        for m in historico
    ]

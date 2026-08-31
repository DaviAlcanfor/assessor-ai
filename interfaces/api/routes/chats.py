"""
Chat API routes

Rotas para chat:
- _validar_ownership: valida se o chat pertence ao usuário
- create_chat: cria um novo chat
- send_message: envia uma mensagem para um chat específico
- get_messages: obtém as mensagens de histórico de um chat específico
"""


from fastapi import APIRouter, Depends, HTTPException, Request, status

from assessor_ai.chat import service as chat_service
from assessor_ai.chat.models import Role as DomainRole
from assessor_ai.chat.service import LimiteDeMensagensExcedido
from config.logging import get_logger
from interfaces.api.auth import get_current_user
from interfaces.api.rate_limiting import limiter
from interfaces.api.schemas.chat import (
    ChatCreateResponse,
    ChatMessageResponse,
    ChatSummary,
    MessageCreate,
    MessageResponse,
    Role,
)

_ROLE_MAP = {
    DomainRole.HUMAN: Role.USER,
    DomainRole.AI: Role.ASSISTANT,
}

logger = get_logger(__name__)


# API Router
# Rota para criar um novo chat e continuar nele
router = APIRouter(prefix="/v1/chats", tags=["chats"])


async def _validar_ownership(chat_id: str, user_id: str) -> None:
    """
    Verifica se um chat pertence ao usuário recebido.
    Lança HTTPException caso o chat não exista ou não pertença ao usuário.
    """
    
    dono = await chat_service.obter_dono_chat(chat_id)

    if dono is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Chat não encontrado.")

    if dono != user_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Chat pertence a outro usuário.")


@router.post("", response_model=ChatCreateResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def create_chat(request: Request, user_id: str = Depends(get_current_user)):
    """
    Cria um chat caso não exista de acordo com o usuário autenticado.
    Retorna o chat_id (session_id) do chat criado.
    """
    
    try:
        chat_id = await chat_service.create_chat(user_id)
        
    except Exception:
        logger.exception(f"Falha ao criar chat para user_id={user_id}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Não foi possível criar o chat.")

    # retorna id do chat criado
    return ChatCreateResponse(chat_id=chat_id)


def _titulo(chat: dict) -> str:
    mensagens = chat.get("messages") or []

    if mensagens and mensagens[0].get("role") == "human":
        conteudo = mensagens[0]["content"]
        return conteudo[:40] + "…" if len(conteudo) > 40 else conteudo

    return "Nova conversa"


@router.get("", response_model=list[ChatSummary])
@limiter.limit("20/minute")
async def list_chats(request: Request, user_id: str = Depends(get_current_user)):
    """
    Lista os chats do usuário autenticado, mais recentes primeiro.
    """

    chats = await chat_service.listar_chats(user_id)

    return [
        ChatSummary(chat_id=c["session_id"], title=_titulo(c), updated_at=c["updated_at"])
        for c in chats
    ]


# Rota para enviar uma mensagem para um chat específico
@router.post("/{chat_id}/messages", response_model=ChatMessageResponse)
@limiter.limit("10/minute")
async def send_message(
    request: Request,
    chat_id: str,
    payload: MessageCreate,
    user_id: str = Depends(get_current_user),
):
    """
    Envia uma mensagem para um chat específico.
    """
    
    await _validar_ownership(chat_id, user_id)

    try:
        resposta = await chat_service.send_message(user_id, chat_id, payload.content)

    except LimiteDeMensagensExcedido as e:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, str(e))

    except Exception:
        logger.exception(f"Falha ao processar mensagem no chat_id={chat_id}")
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Não foi possível processar a mensagem."
        )

    return ChatMessageResponse(chat_id=chat_id, content=resposta)


@router.get("/{chat_id}/messages", response_model=list[MessageResponse])
@limiter.limit("20/minute")
async def get_messages(request: Request, chat_id: str, user_id: str = Depends(get_current_user)):
    """
    Obtém as mensagens de histórico de um chat específico.
    """
    
    await _validar_ownership(chat_id, user_id)

    historico = await chat_service.get_history(chat_id, user_id) or []

    return [
        MessageResponse(role=_ROLE_MAP[m.role], content=m.content)
        for m in historico
    ]

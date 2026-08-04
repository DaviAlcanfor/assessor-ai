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


def _validar_ownership(chat_id: str, user_id: str) -> None:
    """
    Verifica se um chat pertence ao usuário recebido.
    Lança HTTPException caso o chat não exista ou não pertença ao usuário.

    Args:
        chat_id (str): id do chat (session_id)
        user_id (str): id do usuário

    Raises:
        HTTPException: chat não encontrado
        HTTPException: chat pertence a outro usuário
    """
    
    dono = chat_service.obter_dono_chat(chat_id)

    if dono is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Chat não encontrado.")

    if dono != user_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Chat pertence a outro usuário.")


@router.post("", response_model=ChatCreateResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def create_chat(request: Request, user_id: str = Depends(get_current_user)):
    """
    Cria um chat caso não exista de acordo com o usuário autenticado.
    Retorna o chat_id (session_id) do chat criado.
    
    Args:
        request (Request): objeto de requisição do FastAPI
        user_id (str): id do usuário autenticado
    """
    
    try:
        chat_id = chat_service.create_chat(user_id)
        
    except Exception:
        logger.exception(f"Falha ao criar chat para user_id={user_id}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Não foi possível criar o chat.")

    # retorna id do chat criado
    return ChatCreateResponse(chat_id=chat_id)


# Rota para enviar uma mensagem para um chat específico
@router.post("/{chat_id}/messages", response_model=ChatMessageResponse)
@limiter.limit("10/minute")
def send_message(
    request: Request,
    chat_id: str,
    payload: MessageCreate,
    user_id: str = Depends(get_current_user),
):
    """
    Envia uma mensagem para um chat específico.

    Args:
        request (Request): objeto de requisição do FastAPI
        chat_id (str): id do chat (session_id)
        payload (MessageCreate): mensagem enviada pelo usuário
        user_id (str, optional): id do usuario. Defaults to Depends(get_current_user).

    Raises:
        HTTPException: Falha ao processar mensagem no chat_id
        HTTPException: Limite de mensagens excedido

    Returns:
        _type_: ChatMessageResponse - objeto de resposta do chat
    """
    
    _validar_ownership(chat_id, user_id)

    try:
        resposta = chat_service.send_message(user_id, chat_id, payload.content)

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
def get_messages(request: Request, chat_id: str, user_id: str = Depends(get_current_user)):
    """
    Obtém as mensagens de histórico de um chat específico.

    Args:
        request (Request): objeto de requisição do FastAPI
        chat_id (str): id do chat (session_id)
        user_id (str, optional): id do usuário. Defaults to Depends(get_current_user).

    Returns:
        _type_: List[MessageResponse] - lista de mensagens do chat
    """
    
    _validar_ownership(chat_id, user_id)

    historico = chat_service.get_history(chat_id) or []

    return [
        MessageResponse(role=_ROLE_MAP[m.role], content=m.content)
        for m in historico
    ]

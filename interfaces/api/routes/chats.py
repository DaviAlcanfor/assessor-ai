from fastapi import APIRouter, Depends, HTTPException, Request, status

from assessor_ai.chat import service as chat_service
from config.logging import get_logger
from interfaces.api.auth import get_current_user
from interfaces.api.rate_limiting import limiter
from interfaces.api.schemas.chat import (
    ChatCreateResponse,
    ChatMessageResponse,
    MessageCreate,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/v1/chats", tags=["chats"])


def _validar_ownership(chat_id: str, user_id: str) -> None:
    dono = chat_service.obter_dono_chat(chat_id)

    if dono is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Chat não encontrado.")

    if dono != user_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Chat pertence a outro usuário.")


@router.post("", response_model=ChatCreateResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def create_chat(request: Request, user_id: str = Depends(get_current_user)):
    try:
        chat_id = chat_service.create_chat(user_id)
    except Exception:
        logger.exception(f"Falha ao criar chat para user_id={user_id}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Não foi possível criar o chat.")

    return ChatCreateResponse(chat_id=chat_id)


@router.post("/{chat_id}/messages", response_model=ChatMessageResponse)
@limiter.limit("10/minute")
def send_message(
    request: Request,
    chat_id: str,
    payload: MessageCreate,
    user_id: str = Depends(get_current_user),
):
    _validar_ownership(chat_id, user_id)

    try:
        resposta = chat_service.send_message(user_id, chat_id, payload.content)
        
    except Exception:
        logger.exception(f"Falha ao processar mensagem no chat_id={chat_id}")
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR, 
            "Não foi possível processar a mensagem."
        )

    return ChatMessageResponse(chat_id=chat_id, content=resposta)

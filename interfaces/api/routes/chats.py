from fastapi import APIRouter, Depends, Request, status

from chat import service as chat_service
from interfaces.api.auth import get_current_user
from interfaces.api.rate_limiting import limiter
from interfaces.api.schemas.chat import (
    ChatCreateResponse,
    ChatMessageResponse,
    MessageCreate,
)

router = APIRouter(prefix="/v1/chats", tags=["chats"])

@router.post("", response_model=ChatCreateResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def create_chat(request: Request, user_id: str = Depends(get_current_user)):
    chat_id = chat_service.create_chat(user_id)

    return ChatCreateResponse(chat_id=chat_id)


@router.post("/{chat_id}/messages", response_model=ChatMessageResponse)
@limiter.limit("10/minute")
def send_message(
    request: Request,
    chat_id: str,
    payload: MessageCreate,
    user_id: str = Depends(get_current_user),
):
    return ChatMessageResponse(
        chat_id=chat_id,
        content=chat_service.send_message(
            user_id,
            chat_id,
            payload.content
        ),
    )
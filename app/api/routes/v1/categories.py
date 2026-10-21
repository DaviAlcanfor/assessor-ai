"""Rota de leitura das categorias financeiras (pra popular selects no frontend)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from app.api.auth import get_current_user
from app.api.limiter import limiter
from app.domain.types import UserID
from app.services import categoria_service

router = APIRouter(prefix="/v1/categories", tags=["categories"])


class CategoryResponse(BaseModel):
    id: int
    name: str
    description: str | None


@router.get("", response_model=list[CategoryResponse])
@limiter.limit("20/minute")
async def listar_categorias(
    request: Request,
    user_id: Annotated[UserID, Depends(get_current_user)],
) -> list[CategoryResponse]:
    """Todas as categorias cadastradas, ordenadas por nome."""

    return [CategoryResponse(**c) for c in await categoria_service.listar()]


__all__ = ["router"]

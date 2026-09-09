"""
Rotas do formulário de perfil financeiro (`web/src/pages/perfil-page.tsx`).

`user_id` vem sempre de `get_current_user` (mesmo contrato do resto de `/v1`), nunca do corpo.
O agente financeiro só LÊ esse cadastro, via tool `consultar_perfil_financeiro`; a única
escrita é o `PUT` aqui — o cadastro é um por usuário, então salvar de novo substitui.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from assessor_ai.api.auth import get_current_user
from assessor_ai.api.limiter import limiter
from assessor_ai.identifiers import UserID
from assessor_ai.schemas.perfil import PerfilCreate, PerfilResponse
from assessor_ai.services import chat_service

router = APIRouter(prefix="/v1/perfil", tags=["perfil"])


@router.put("", response_model=PerfilResponse)
@limiter.limit("10/minute")
async def salvar_perfil(
    request: Request,
    payload: PerfilCreate,
    user_id: Annotated[UserID, Depends(get_current_user)],
) -> PerfilResponse:
    """Grava o cadastro (Mongo) e indexa as preferências em texto livre (Qdrant)."""

    registro = await chat_service.salvar_perfil_financeiro(
        user_id=user_id,
        renda_mensal=payload.renda_mensal,
        objetivo=payload.objetivo,
        tolerancia_risco=payload.tolerancia_risco,
        preferencias=payload.preferencias,
    )

    return PerfilResponse(**registro)


@router.get("", response_model=PerfilResponse)
@limiter.limit("20/minute")
async def obter_perfil(
    request: Request,
    user_id: Annotated[UserID, Depends(get_current_user)],
) -> PerfilResponse:
    """Cadastro atual do usuário, pra tela pré-preencher o formulário. 404 se ainda não existe."""

    registro = await chat_service.obter_perfil_financeiro(user_id)

    if registro is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Perfil ainda não cadastrado.")

    return PerfilResponse(**registro)


__all__ = ["router"]

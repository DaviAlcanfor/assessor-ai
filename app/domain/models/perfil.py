from typing import Literal, TypedDict

from pydantic import BaseModel

from app.domain.types import UserID

ToleranciaRisco = Literal["baixa", "media", "alta"]


class PerfilFinanceiroDocument(BaseModel):
    """Formato validado antes de gravar no Mongo — construído só pela rota HTTP `/v1/perfil`."""

    user_id: UserID
    renda_mensal: float
    objetivo: str
    tolerancia_risco: ToleranciaRisco
    preferencias: str | None = None


class PerfilFinanceiroRecord(TypedDict):
    """Formato lido de volta do Mongo (`find_one`) e devolvido pela rota."""

    user_id: UserID
    renda_mensal: float
    objetivo: str
    tolerancia_risco: ToleranciaRisco
    preferencias: str | None


__all__ = ["PerfilFinanceiroDocument", "PerfilFinanceiroRecord", "ToleranciaRisco"]

from typing import Literal, TypedDict

from pydantic import BaseModel, Field

from assessor_ai.identifiers import UserID

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


class ConsultarPerfilArgs(BaseModel):
    pergunta: str = Field(
        description="Pergunta ou tópico atual do usuário — usado para buscar, por "
        "similaridade semântica, as preferências relevantes do cadastro."
    )


__all__ = [
    "ConsultarPerfilArgs",
    "PerfilFinanceiroDocument",
    "PerfilFinanceiroRecord",
    "ToleranciaRisco",
]

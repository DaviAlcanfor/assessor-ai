from pydantic import BaseModel, Field

from assessor_ai.graph.tools.perfil.schemas import ToleranciaRisco


class PerfilCreate(BaseModel):
    renda_mensal: float = Field(gt=0)
    objetivo: str = Field(min_length=1, max_length=120)
    tolerancia_risco: ToleranciaRisco
    preferencias: str | None = Field(default=None, max_length=2000)


class PerfilResponse(BaseModel):
    renda_mensal: float
    objetivo: str
    tolerancia_risco: ToleranciaRisco
    preferencias: str | None = None


__all__ = ["PerfilCreate", "PerfilResponse"]

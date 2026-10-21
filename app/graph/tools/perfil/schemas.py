from pydantic import BaseModel, Field


class ConsultarPerfilArgs(BaseModel):
    pergunta: str = Field(
        description="Pergunta ou tópico atual do usuário — usado para buscar, por "
        "similaridade semântica, as preferências relevantes do cadastro."
    )


__all__ = ["ConsultarPerfilArgs"]

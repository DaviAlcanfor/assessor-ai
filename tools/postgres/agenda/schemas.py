from typing import Optional
from pydantic import BaseModel, Field


class AddEventArgs(BaseModel):
    title: str = Field(..., description="Título do evento.")
    start_time: str = Field(..., description="Timestamp ISO 8601 de início do evento.")
    source_text: str = Field(..., description="Texto original do usuário.")
    notes: str = Field(..., description="Observações sobre o evento.")
    end_time: Optional[str] = Field(default=None, description="Timestamp ISO 8601 de fim do evento.")
    location: Optional[str] = Field(default=None, description="Local do evento.")


class QueryEventArgs(BaseModel):
    date_from_local: Optional[str] = Field(default=None, description="Data local (America/Sao_Paulo) inicial para filtrar eventos.")
    date_to_local: Optional[str] = Field(default=None, description="Data local (America/Sao_Paulo) final para filtrar eventos.")
    title: Optional[str] = Field(default=None, description="Texto para buscar em title ou notes (filtro de texto).")


class UpdateEventArgs(BaseModel):
    id: Optional[int] = Field(
        default=None,
        description="ID do evento a atualizar. Se ausente, será feita busca por (match_text + date_local)."
    )
    match_text: Optional[str] = Field(
        default=None,
        description="Texto para localizar evento quando id não for informado (busca em title/notes)."
    )
    date_local: Optional[str] = Field(
        default=None,
        description="Data local (YYYY-MM-DD) em America/Sao_Paulo; usado com match_text quando id ausente."
    )
    title: Optional[str] = Field(default=None, description="Novo título.")
    start_time: Optional[str] = Field(default=None, description="Novo timestamp ISO 8601 de início.")
    end_time: Optional[str] = Field(default=None, description="Novo timestamp ISO 8601 de fim.")
    location: Optional[str] = Field(default=None, description="Novo local.")
    notes: Optional[str] = Field(default=None, description="Novas observações.")
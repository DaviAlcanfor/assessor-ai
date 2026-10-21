from pydantic import BaseModel, Field


class FaqRetrieverArgs(BaseModel):
    question: str = Field(..., description="Pergunta do usuário sobre o Assessor.AI.")


__all__ = ["FaqRetrieverArgs"]

from pydantic import BaseModel, Field


class FaqRetrieverArgs(BaseModel):
    question: str = Field(..., description="Pergunta do usuário sobre o Assessor.AI.")


class SearchResponse(BaseModel):
    text: str
    file: str
    page: int
    score: float
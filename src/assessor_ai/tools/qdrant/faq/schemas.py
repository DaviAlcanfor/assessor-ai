from pydantic import BaseModel, Field

class SearchResponse(BaseModel):
    text: str
    file: str
    page: int
    score: float
from pydantic import BaseModel


class SearchResponse(BaseModel):
    text: str
    file: str
    page: int
    score: float
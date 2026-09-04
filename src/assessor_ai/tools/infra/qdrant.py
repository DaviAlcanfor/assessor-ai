"""
Conexão com o Qdrant e o modelo de embedding das buscas.

O `GoogleGenerativeAIEmbeddings` fica aqui, e não dentro da tool, porque antes era reconstruído
a cada pergunta do FAQ — objeto de client, não de request.
"""

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from qdrant_client import QdrantClient

from assessor_ai.core.config import settings
from assessor_ai.core.models import Model

# precisa bater com o da collection (ver faq/ingest.py:_VECTOR_SIZE)
VECTOR_SIZE = 768
_TASK_TYPE_QUERY = "retrieval_query"


class QdrantConn:
    def __init__(self) -> None:
        self._client: QdrantClient | None = None
        self._embeddings: GoogleGenerativeAIEmbeddings | None = None

    @property
    def client(self) -> QdrantClient:
        if self._client is None:
            self._client = QdrantClient(
                url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY.get_secret_value()
            )

        return self._client

    @property
    def embeddings(self) -> GoogleGenerativeAIEmbeddings:
        if self._embeddings is None:
            self._embeddings = GoogleGenerativeAIEmbeddings(
                model=Model.EMBEDDING_MODEL,
                google_api_key=settings.GEMINI_API_KEY.get_secret_value(),
                task_type=_TASK_TYPE_QUERY,
                output_dimensionality=VECTOR_SIZE,
            )

        return self._embeddings


qdrant = QdrantConn()


__all__ = ["VECTOR_SIZE", "QdrantConn", "qdrant"]

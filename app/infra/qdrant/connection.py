"""
Conexão com o Qdrant e o modelo de embedding das buscas.

O `GoogleGenerativeAIEmbeddings` fica aqui, e não dentro da tool, porque antes era reconstruído
a cada pergunta do FAQ — objeto de client, não de request.
"""

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from qdrant_client import QdrantClient

from app.infra.base import Conector
from app.settings import settings
from app.settings.llm import Model

VECTOR_SIZE = 768


class QdrantConn(Conector[QdrantClient]):
    _TASK_TYPE_QUERY = "retrieval_query"
    _TASK_TYPE_DOCUMENT = "retrieval_document"

    def __init__(self) -> None:
        self._client: QdrantClient | None = None
        self._embeddings: GoogleGenerativeAIEmbeddings | None = None
        self._embeddings_documento: GoogleGenerativeAIEmbeddings | None = None

    def conectar(self) -> QdrantClient:
        if self._client is None:
            self._client = QdrantClient(
                url=settings.database.qdrant_url, api_key=settings.database.qdrant_api_key.get_secret_value() or None
            )

        return self._client

    @property
    def client(self) -> QdrantClient:
        return self.conectar()

    @property
    def embeddings(self) -> GoogleGenerativeAIEmbeddings:
        if self._embeddings is None:
            self._embeddings = GoogleGenerativeAIEmbeddings(
                model=Model.EMBEDDING_MODEL,
                google_api_key=settings.llm.gemini.api_key.get_secret_value(),
                task_type=self._TASK_TYPE_QUERY,
                output_dimensionality=VECTOR_SIZE,
            )

        return self._embeddings

    @property
    def embeddings_documento(self) -> GoogleGenerativeAIEmbeddings:
        """
        Mesma dimensão, `task_type` de indexação. O FAQ usa o par query/document equivalente
        (`faq/ingest.py`), mas lá a indexação roda num script offline. Perfil indexa a partir da
        própria rota (o cadastro é escrito a qualquer momento, não por lote), então o lado
        `document` precisa estar disponível em runtime, não só no script de ingestão.
        """

        if self._embeddings_documento is None:
            self._embeddings_documento = GoogleGenerativeAIEmbeddings(
                model=Model.EMBEDDING_MODEL,
                google_api_key=settings.llm.gemini.api_key.get_secret_value(),
                task_type=self._TASK_TYPE_DOCUMENT,
                output_dimensionality=VECTOR_SIZE,
            )

        return self._embeddings_documento


qdrant = QdrantConn()


__all__ = ["VECTOR_SIZE", "QdrantConn", "qdrant"]

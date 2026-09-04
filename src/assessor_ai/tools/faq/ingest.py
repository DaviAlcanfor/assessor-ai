"""Ingestão do PDF de FAQ para a collection do Qdrant. Rodar sob demanda:
python -m assessor_ai.tools.faq.ingest
"""

import time
from pathlib import Path
from uuid import NAMESPACE_DNS, uuid5

from langchain_community.document_loaders import PyPDFLoader
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from assessor_ai.core.config import settings
from assessor_ai.core.logging import get_logger
from assessor_ai.core.models import Model
from assessor_ai.tools.infra.qdrant import VECTOR_SIZE, qdrant

logger = get_logger("qdrant_ingest")

_PDF_PATH = Path("data/documents/FAQ_assessor_v1.1.pdf")
_CHUNK_SIZE = 700
_CHUNK_OVERLAP = 150
_VECTOR_SIZE = VECTOR_SIZE  # mesma constante que a busca usa (infra/qdrant.py)
_TASK_TYPE_DOCUMENT = "retrieval_document"
_EMBED_BATCH = 20
_EMBED_PAUSE_S = 20  # gemini-embedding-001 tem cota por minuto baixa; pausa entre lotes


def _load_faq_pdf() -> tuple[GoogleGenerativeAIEmbeddings, list]:
    loader = PyPDFLoader(_PDF_PATH)

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=_CHUNK_SIZE,
        chunk_overlap=_CHUNK_OVERLAP,
    )

    chunks = text_splitter.split_documents(loader.load())

    embeddings = GoogleGenerativeAIEmbeddings(
        model=Model.EMBEDDING_MODEL,
        google_api_key=settings.GEMINI_API_KEY.get_secret_value(),
        task_type=_TASK_TYPE_DOCUMENT,
        output_dimensionality=_VECTOR_SIZE,
    )

    return embeddings, chunks


def _embed_em_lotes(embeddings: GoogleGenerativeAIEmbeddings, textos: list[str]) -> list[list[float]]:
    vetores: list[list[float]] = []
    for i in range(0, len(textos), _EMBED_BATCH):
        if i:
            time.sleep(_EMBED_PAUSE_S)
        vetores.extend(embeddings.embed_documents(textos[i : i + _EMBED_BATCH]))
    return vetores


def _ensure_collection_exists(client: QdrantClient) -> None:
    if not client.collection_exists(settings.QDRANT_COLLECTION_NAME):
        client.create_collection(
            collection_name=settings.QDRANT_COLLECTION_NAME,
            vectors_config=VectorParams(size=_VECTOR_SIZE, distance=Distance.COSINE),
        )


def _store_documents_in_qdrant(
    client: QdrantClient,
    embeddings: GoogleGenerativeAIEmbeddings,
    chunks: list,
) -> None:
    textos = [chunk.page_content for chunk in chunks]
    vetores = _embed_em_lotes(embeddings, textos)

    pontos = [
        PointStruct(
            id=str(uuid5(NAMESPACE_DNS, texto)),
            vector=vetor,
            payload={
                "text": chunk.page_content,
                "file": chunk.metadata.get("source", ""),
                "page": chunk.metadata.get("page", 0),
            },
        )
        for texto, vetor, chunk in zip(textos, vetores, chunks, strict=True)
    ]

    client.upsert(collection_name=settings.QDRANT_COLLECTION_NAME, points=pontos)


def ingest() -> None:
    client = qdrant.client
    embeddings, chunks = _load_faq_pdf()

    _ensure_collection_exists(client)
    _store_documents_in_qdrant(client, embeddings, chunks)

    logger.info("INGESTÃO OK | collection=%s chunks=%d", settings.QDRANT_COLLECTION_NAME, len(chunks))


if __name__ == "__main__":
    ingest()

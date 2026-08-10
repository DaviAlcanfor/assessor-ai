from pathlib import Path
from uuid import NAMESPACE_DNS, uuid5

from langchain_community.document_loaders import PyPDFLoader
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from config import settings
from config.models import Model

from .connection import get_qdrant_client
from .schemas import SearchResponse

_PDF_PATH = Path("data/documents/FAQ_assessor_v1.1.pdf")

_CHUNK_SIZE = 700
_CHUNK_OVERLAP = 150
_K_NUMBER = 5

_VECTOR_SIZE = 768
_TASK_TYPE_DOCUMENT = "retrieval_document"
_TASK_TYPE_QUERY = "retrieval_query"
_COLLECTION = "faq_assessor"



def _load_faq_pdf() -> tuple[GoogleGenerativeAIEmbeddings, list]:
    loader = PyPDFLoader(_PDF_PATH)

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=_CHUNK_SIZE,
        chunk_overlap=_CHUNK_OVERLAP
    )

    loaded_documents = loader.load()
    chunks = text_splitter.split_documents(loaded_documents)

    embeddings = GoogleGenerativeAIEmbeddings(
        model=Model.EMBEDDING_MODEL,
        google_api_key=settings.GEMINI_API_KEY,
        task_type=_TASK_TYPE_DOCUMENT
    )

    return embeddings, chunks


def _ensure_collection_exists(client: QdrantClient) -> None:
    if not client.collection_exists(_COLLECTION):
        client.create_collection(
            collection_name=_COLLECTION,
            vectors_config=VectorParams(
                size=_VECTOR_SIZE,
                distance=Distance.COSINE
            ),
        )


def _store_documents_in_qdrant(
    client: QdrantClient, 
    embeddings: GoogleGenerativeAIEmbeddings, 
    chunks: list
) -> None:
    
    textos = [chunk.page_content for chunk in chunks]
    vetores = embeddings.embed_documents(textos)

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
        for texto, vetor, chunk in zip(textos, vetores, chunks)
    ]

    client.upsert(collection_name=_COLLECTION, points=pontos)
    

def buscar(query: str) -> list[SearchResponse]:
    client = get_qdrant_client()

    embeddings = GoogleGenerativeAIEmbeddings(
        model=Model.EMBEDDING_MODEL,
        google_api_key=settings.GEMINI_API_KEY,
        task_type=_TASK_TYPE_QUERY
    )

    vetor = embeddings.embed_query(query)

    resultados = client.query_points(
        collection_name=_COLLECTION,
        query=vetor,
        limit=_K_NUMBER,
    ).points

    return [
        SearchResponse(
            text=r.payload["text"],
            file=r.payload["file"],
            page=r.payload["page"],
            score=r.score,
        )
        for r in resultados
    ]
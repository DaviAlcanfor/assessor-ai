import os
from pathlib import Path
from langchain.tools import tool
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from config.settings import settings
from config.models import Model


_PDF_PATH     = Path("data/documents/FAQ_assessor_v1.1.pdf")
_CHUNK_SIZE    = 700
_CHUNK_OVERLAP = 150


def _build_index() -> FAISS:

    loader = PyPDFLoader(_PDF_PATH)
    chunks = RecursiveCharacterTextSplitter(
        chunk_size=_CHUNK_SIZE,
        chunk_overlap=_CHUNK_OVERLAP
    ).split_documents(loader.load())

    embeddings = GoogleGenerativeAIEmbeddings(
        model=Model.EMBEDDING_MODEL,
        google_api_key=settings.GEMINI_API_KEY,
        task_type="retrieval_document"
    )

    return FAISS.from_documents(chunks, embeddings)


_INDEX = _build_index()


@tool("faq_retriever")
def faq_retriever(question: str) -> str:
    """Consulta o PDF de FAQ com as perguntas de funcionamento do Assessor AI."""

    results = _INDEX.similarity_search(question, k=5)
    return "\n\n".join(res.page_content for res in results)
import os
from dotenv import load_dotenv
from langchain.tools import tool
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from config.settings import GEMINI_API_KEY
from config.models import EMBEDDING_MODEL

load_dotenv()


PDF_PATH = os.getenv("rag_docs", "FAQ_assessor_v1.1.pdf")
CHUNK_SIZE = 700
CHUNK_OVERLAP = 150

@tool("faq_retriever")
def faq_retriever(question: str) -> str:
    """Consulta o PDF de FAQ com as perguntas de funcionamento do Assessor AI"""
    
    loader = PyPDFLoader(PDF_PATH)
    docs = loader.load()
    
    splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE,
                                              chunk_overlap=CHUNK_OVERLAP)
    chunks = splitter.split_documents(docs)
    
    embeddings = GoogleGenerativeAIEmbeddings(
        model=EMBEDDING_MODEL,
        google_api_key=GEMINI_API_KEY
    )
    
    db = FAISS.from_documents(chunks, embeddings)
    
    results = db.similarity_search(question, k=5)
    
    return "\n\n".join([res.page_content for res in results])

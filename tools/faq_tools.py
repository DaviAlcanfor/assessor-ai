import os
from dotenv import load_dotenv
from langchain.tools import tool
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAI


load_dotenv()


PDF_PATH = os.getenv("rag", "FAQ_assessor_v1.1.pdf")

@tool()
def faq_retriever(question: str) -> str:
    pass
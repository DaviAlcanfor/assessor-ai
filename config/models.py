from enum import StrEnum

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq

from .settings import settings


class Model(StrEnum):
    GEMINI_2_5_FLASH    = "gemini-2.5-flash"
    GPT_OSS_120B        = "openai/gpt-oss-120b"
    QWEN_2_5_PRO        = "qwen-2.5-pro"
    CLAUDE_HAIKU        = "claude-haiku-4-5"
    CLAUDE_SONNET       = "claude-sonnet-4-6"
    EMBEDDING_MODEL     = "gemini-embedding-001"
    


PROVIDER_MAP = {
    Model.GEMINI_2_5_FLASH:    "gemini",
    Model.GPT_OSS_120B:        "groq",
    Model.QWEN_2_5_PRO:        "groq",
    Model.CLAUDE_HAIKU:        "claude",
    Model.CLAUDE_SONNET:       "claude",
}

API_KEYS = {
    "gemini": settings.GEMINI_API_KEY,
    "groq":   settings.GROQ_API_KEY,
}

BUILDERS = {
    "gemini": ChatGoogleGenerativeAI,
    "groq":   ChatGroq,
}
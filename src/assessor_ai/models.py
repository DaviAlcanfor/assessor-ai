"""Catálogo de modelos e qual provider/classe LangChain atende cada um. Chave, URL e timeout
de cada provider ficam em `config.py:LLMSettings` (`settings.llm.<provider>`)."""

from collections.abc import Callable, Mapping
from enum import StrEnum
from typing import Literal

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI

# O nome bate com o campo de `LLMSettings`: `getattr(settings.llm, provider)`.
type Provider = Literal["gemini", "groq", "claude", "gateway"]


class Model(StrEnum):
    GEMINI_2_5_FLASH     = "gemini-2.5-flash"
    GPT_OSS_120B         = "openai/gpt-oss-120b"
    QWEN_2_5_PRO         = "qwen-2.5-pro"
    GPT_6_LUNA           = "openai/gpt-6-luna"
    GPT_6_LUNA_DECISIONS = "openai/gpt-6-luna-decisions"  # reserva do JeV dentro do gateway
    JEV                  = "typesafe-ai/jev"              # Decisions API, não é chat model
    CLAUDE_HAIKU         = "claude-haiku-4-5"
    CLAUDE_SONNET        = "claude-sonnet-4-6"
    EMBEDDING_MODEL      = "gemini-embedding-001"


PROVIDER_MAP: Mapping[Model, Provider] = {
    Model.GEMINI_2_5_FLASH: "gemini",
    Model.GPT_OSS_120B:     "groq",
    Model.QWEN_2_5_PRO:     "groq",
    Model.GPT_6_LUNA:       "gateway",
    Model.CLAUDE_HAIKU:     "claude",
    Model.CLAUDE_SONNET:    "claude",
}

BUILDERS: Mapping[Provider, Callable[..., BaseChatModel]] = {
    "gemini":  ChatGoogleGenerativeAI,
    "groq":    ChatGroq,
    "claude":  ChatAnthropic,
    "gateway": ChatOpenAI,  # o gateway da Vercel é OpenAI-compatible
}

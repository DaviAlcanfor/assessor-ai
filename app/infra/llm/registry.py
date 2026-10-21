"""Qual provider atende cada modelo e qual classe LangChain o constrói."""

from collections.abc import Callable, Mapping
from typing import Literal

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI

from app.settings.llm import Model

# O nome bate com o campo de `LLMSettings`: `getattr(settings.llm, provider)`.
type Provider = Literal["gemini", "groq", "claude", "gateway"]

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

__all__ = ["BUILDERS", "PROVIDER_MAP", "Provider"]

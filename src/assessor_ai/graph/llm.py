
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq

from assessor_ai.core.models import API_KEYS, BUILDERS, PROVIDER_MAP, Model


def build_llm(
    temperature: float,
    top_p: float | None = None,
    model: Model | None = None
) -> ChatGoogleGenerativeAI | ChatGroq | ChatAnthropic:
    """
    Cria uma LLM com base no modelo informado.
    top_p só é aplicado para modelos Gemini.
    """

    if model is None:
        raise ValueError("Modelo não informado")

    provider = PROVIDER_MAP.get(model)

    if provider is None:
        raise ValueError(f"Modelo desconhecido: {model}")

    kwargs = {
        "model": model,
        "temperature": temperature,
        "api_key": API_KEYS.get(provider),
    }

    if top_p is not None and provider == "gemini":
        kwargs["top_p"] = top_p

    # gpt-oss é modelo de raciocínio: sem isso o chain-of-thought vem dentro do content
    # e polui os regex de ROUTE= (nodes/router.py) e RESPOSTA: (guardrail de saída).
    if provider == "groq":
        kwargs["reasoning_format"] = "hidden"

    return BUILDERS[provider](**kwargs)



llm_gemini = build_llm(model=Model.GEMINI_2_5_FLASH, temperature=0.7, top_p=0.95)
llm_groq   = build_llm(model=Model.GPT_OSS_120B, temperature=0.7)
llm_rapido = build_llm(model=Model.GPT_OSS_120B, temperature=0.0)
llm_guardrail = build_llm(model=Model.GEMINI_2_5_FLASH, temperature=0.0)
llm_especialista = llm_gemini.with_fallbacks([llm_groq])



__all__ = [
    "llm_especialista",
    "llm_gemini",
    "llm_groq",
    "llm_guardrail",
    "llm_rapido",
]
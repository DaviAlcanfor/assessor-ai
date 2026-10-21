from typing import Any

from langchain_core.language_models import BaseChatModel, LanguageModelInput
from langchain_core.messages import BaseMessage
from langchain_core.runnables import Runnable

from assessor_ai.config import LLMSettings, Provedor, settings
from assessor_ai.models import BUILDERS, PROVIDER_MAP, Model

_cfg = settings.llm


def build_llm(
    model: Model,
    temperature: float,
    llm_settings: LLMSettings = _cfg,
    top_p: float | None = None,
    timeout_s: float | None = None,
) -> BaseChatModel | None:
    """
    Cria uma LLM com base no modelo informado.
    top_p só é aplicado para modelos Gemini.
    `timeout_s` sobrepõe o timeout do provider (`settings.llm.<provider>`) — usado pelos
    papéis de saída curta, que não devem esperar tanto quanto um especialista.
    Devolve None se o provider não tiver API key configurada (providers opcionais).
    """

    provider = PROVIDER_MAP.get(model)
    if provider is None:
        raise ValueError(f"Modelo desconhecido: {model}")

    cfg: Provedor = getattr(llm_settings, provider)
    if not cfg.api_key.get_secret_value():
        return None

    kwargs: dict[str, Any] = {
        "model": model.value,
        "temperature": temperature,
        "api_key": cfg.api_key.get_secret_value(),
        "timeout": timeout_s if timeout_s is not None else cfg.timeout_s,
        # No Gemini `max_retries` conta tentativas TOTAIS (1 = sem retry); nos SDKs da
        # Groq/OpenAI/Anthropic conta as EXTRAS. A política usa sempre "extras".
        "max_retries": cfg.retries + 1 if provider == "gemini" else cfg.retries,
    }

    if cfg.base_url:
        kwargs["base_url"] = cfg.base_url

    if top_p is not None and provider == "gemini":
        kwargs["top_p"] = top_p

    # gpt-oss é modelo de raciocínio: sem isso o chain-of-thought vem dentro do content
    # e polui os regex de ROUTE= (nodes/router.py) e RESPOSTA: (guardrail de saída).
    if provider == "groq":
        kwargs["reasoning_format"] = "hidden"

    return BUILDERS[provider](**kwargs)


def com_reserva(*modelos: BaseChatModel | None) -> Runnable[LanguageModelInput, BaseMessage]:
    """O primeiro modelo disponível, com os demais de fallback (`None` = provider sem chave)."""

    cadeia = [m for m in modelos if m is not None]
    if not cadeia:
        raise ValueError("Nenhum modelo da cadeia tem API key configurada")
    return cadeia[0].with_fallbacks(cadeia[1:]) if cadeia[1:] else cadeia[0]


# Luna vai sempre por último: sem cartão na conta Vercel ele responde 403 e só atrasa a cadeia.
llm_luna   = build_llm(Model.GPT_6_LUNA, temperature=0.7)
llm_gemini = build_llm(Model.GEMINI_2_5_FLASH, temperature=0.7, top_p=0.95)
llm_groq   = build_llm(Model.GPT_OSS_120B, temperature=0.7)

llm_especialista = com_reserva(llm_gemini, llm_groq, llm_luna)
llm_rapido = com_reserva(
    build_llm(Model.GPT_OSS_120B, temperature=0.0, timeout_s=_cfg.timeout_curto_s),
    llm_luna,
)
llm_guardrail = com_reserva(
    build_llm(Model.GEMINI_2_5_FLASH, temperature=0.0, timeout_s=_cfg.timeout_curto_s),
    llm_luna,
)


__all__ = [
    "build_llm",
    "com_reserva",
    "llm_especialista",
    "llm_gemini",
    "llm_groq",
    "llm_guardrail",
    "llm_luna",
    "llm_rapido",
]

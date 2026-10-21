from langchain_core.language_models import BaseChatModel, LanguageModelInput
from langchain_core.messages import BaseMessage
from langchain_core.runnables import Runnable

from assessor_ai.infra.llm import build_llm
from assessor_ai.settings import settings
from assessor_ai.settings.llm import Model

_cfg = settings.llm


def com_reserva(*modelos: BaseChatModel | None) -> Runnable[LanguageModelInput, BaseMessage]:
    """O primeiro modelo disponível, com os demais de fallback (`None` = provider sem chave)."""

    cadeia = [m for m in modelos if m is not None]
    if not cadeia:
        raise ValueError("Nenhum modelo da cadeia tem API key configurada")
    return cadeia[0].with_fallbacks(cadeia[1:]) if cadeia[1:] else cadeia[0]


# Luna vai sempre por último: sem cartão na conta Vercel ele responde 403 e só atrasa a cadeia.
llm_luna   = build_llm(Model.GPT_6_LUNA, _cfg.default_temperature, _cfg)
llm_gemini = build_llm(Model.GEMINI_2_5_FLASH, _cfg.default_temperature, _cfg, top_p=0.95)
llm_groq   = build_llm(Model.GPT_OSS_120B, _cfg.default_temperature, _cfg)

llm_especialista = com_reserva(llm_gemini, llm_groq, llm_luna)
llm_rapido = com_reserva(
    build_llm(Model.GPT_OSS_120B, _cfg.guardrail_temperature, _cfg, timeout_s=_cfg.timeout_curto_s),
    llm_luna,
)
llm_guardrail = com_reserva(
    build_llm(Model.GEMINI_2_5_FLASH, _cfg.guardrail_temperature, _cfg, timeout_s=_cfg.timeout_curto_s),
    llm_luna,
)


__all__ = [
    "com_reserva",
    "llm_especialista",
    "llm_gemini",
    "llm_groq",
    "llm_guardrail",
    "llm_luna",
    "llm_rapido",
]

from enum import StrEnum

from pydantic import BaseModel, SecretStr


class Model(StrEnum):
    """Catálogo de modelos — dado puro, sem dependência de LangChain."""

    GEMINI_2_5_FLASH     = "gemini-2.5-flash"
    GPT_OSS_120B         = "openai/gpt-oss-120b"
    QWEN_2_5_PRO         = "qwen-2.5-pro"
    GPT_6_LUNA           = "openai/gpt-6-luna"
    GPT_6_LUNA_DECISIONS = "openai/gpt-6-luna-decisions"  # reserva do JeV dentro do gateway
    JEV                  = "typesafe-ai/jev"              # Decisions API, não é chat model
    CLAUDE_HAIKU         = "claude-haiku-4-5"
    CLAUDE_SONNET        = "claude-sonnet-4-6"
    EMBEDDING_MODEL      = "gemini-embedding-001"


class Provedor(BaseModel):
    """Chave, URL e paciência de um provider. `retries` são tentativas extras: pior caso
    `(retries + 1) * timeout_s` antes do `with_fallbacks` passar pro próximo."""

    api_key:   SecretStr = SecretStr("")
    base_url:  str | None = None
    timeout_s: float = 30.0
    retries:   int = 0


class GeminiSettings(Provedor):
    """Principal dos especialistas e do guardrail; também gera os embeddings."""

    api_key: SecretStr


class GroqSettings(Provedor):
    """Primeira reserva e o `llm_rapido`. 429 por rajada costuma passar em segundos, daí 1 retry."""

    api_key: SecretStr
    retries: int = 1


class ClaudeSettings(Provedor):
    """Opcional, fora das cadeias por padrão."""

    timeout_s: float = 60.0
    retries:   int = 1


class GatewaySettings(Provedor):
    """Vercel AI Gateway: GPT-6 Luna no fim das cadeias e JeV no guardrail e no roteador.
    Opcional: sem chave os dois ficam de fora. Luna raciocina, é mais lento."""

    base_url:  str = "https://ai-gateway.vercel.sh/v1"
    timeout_s: float = 45.0
    retries:   int = 1


class LLMSettings(BaseModel):
    gemini:  GeminiSettings
    groq:    GroqSettings
    claude:  ClaudeSettings = ClaudeSettings()
    gateway: GatewaySettings = GatewaySettings()

    # Teto por papel, acima do timeout do provider: saída curta (guardrail, roteador, JeV)
    # não espera tanto quanto um especialista.
    timeout_curto_s: float = 15.0

    default_temperature:   float = 0.7
    guardrail_temperature: float = 0.0

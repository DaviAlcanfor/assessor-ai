import pytest
from pydantic import ValidationError

from assessor_ai.settings import Settings

_OBRIGATORIAS = {
    "DATABASE__POSTGRES_URL": "postgresql://u:p@h/db",
    "DATABASE__MONGO_URL": "mongodb://h/",
    "DATABASE__MONGO_COLLECTION_NAME": "c",
    "DATABASE__REDIS_URL": "redis://h/0",
    "DATABASE__QDRANT_URL": "http://h:6333",
    "DATABASE__QDRANT_COLLECTION_NAME": "c",
    "API_KEYS__SIGNUP_SECRET": "s",
    "LLM__GEMINI__API_KEY": "g",
    "LLM__GROQ__API_KEY": "q",
}


@pytest.fixture
def ambiente(monkeypatch):
    """Ambiente mínimo e limpo: só as obrigatórias, sem `.env` e sem sobras de outros testes."""

    for nome in list(__import__("os").environ):
        if nome.startswith(("DATABASE__", "API__", "API_KEYS__", "LLM__", "OBSERVABILITY__", "ENVIRONMENT")):
            monkeypatch.delenv(nome)
    for nome, valor in _OBRIGATORIAS.items():
        monkeypatch.setenv(nome, valor)
    return monkeypatch


def _settings() -> Settings:
    return Settings(_env_file=None)  # type: ignore[call-arg]


def test_delimitador_aninha_grupos_e_provedores(ambiente):
    ambiente.setenv("LLM__GATEWAY__TIMEOUT_S", "99")
    ambiente.setenv("API__SESSION_TTL_SECONDS", "60")

    cfg = _settings()

    assert cfg.database.postgres_url.get_secret_value() == "postgresql://u:p@h/db"
    assert cfg.llm.gateway.timeout_s == 99
    assert cfg.api.session_ttl_seconds == 60


def test_gateway_e_claude_sao_opcionais_e_ficam_sem_chave(ambiente):
    cfg = _settings()

    assert not cfg.llm.gateway.api_key.get_secret_value()
    assert not cfg.llm.claude.api_key.get_secret_value()


def test_segredos_nao_aparecem_no_repr(ambiente):
    assert "postgresql://u:p@h/db" not in repr(_settings())


def test_falta_de_variavel_obrigatoria_falha(ambiente):
    ambiente.delenv("DATABASE__POSTGRES_URL")

    with pytest.raises(ValidationError):
        _settings()


@pytest.mark.parametrize(
    ("nome", "valor"),
    [
        ("API__KEY_AUTH_ENABLED", "false"),
        ("API__SESSION_COOKIE_SECURE", "false"),
        ("API__CORS_ORIGINS", '["*"]'),
    ],
)
def test_producao_recusa_config_insegura(ambiente, nome, valor):
    ambiente.setenv("ENVIRONMENT", "production")
    ambiente.setenv("API__CORS_ORIGINS", '["https://app.exemplo.com"]')
    ambiente.setenv(nome, valor)

    with pytest.raises(ValidationError):
        _settings()


def test_producao_aceita_config_segura(ambiente):
    ambiente.setenv("ENVIRONMENT", "production")
    ambiente.setenv("API__CORS_ORIGINS", '["https://app.exemplo.com"]')

    assert _settings().environment == "production"

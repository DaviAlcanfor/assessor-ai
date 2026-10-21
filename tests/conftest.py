import pytest
from pydantic import SecretStr

from assessor_ai.config import settings


@pytest.fixture(autouse=True)
def _sem_gateway(monkeypatch):
    """Teste nunca fala com o Vercel AI Gateway de verdade, mesmo com a chave no .env:
    JeV desligado por padrão — quem testa o JeV liga com a chave fake e o HTTP stubado."""

    monkeypatch.setattr(settings.llm.gateway, "api_key", SecretStr(""))

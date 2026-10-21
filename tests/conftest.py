"""
`Settings()` roda no import de `assessor_ai`, então as variáveis obrigatórias precisam existir antes
dele. `setdefault` deixa uma variável real do ambiente (ex.: Infisical) ter prioridade sobre o dummy,
e o `.env` nunca é lido pra valores que já estão aqui — teste não depende do `.env` de ninguém.
"""

import os

for _nome, _valor in {
    "DATABASE__POSTGRES_URL": "postgresql://user:pass@localhost:5432/db",
    "DATABASE__MONGO_URL": "mongodb://localhost:27017/",
    "DATABASE__MONGO_COLLECTION_NAME": "assessor",
    "DATABASE__REDIS_URL": "redis://localhost:6379/0",
    "DATABASE__QDRANT_URL": "http://localhost:6333",
    "DATABASE__QDRANT_COLLECTION_NAME": "assessor",
    "API_KEYS__SIGNUP_SECRET": "dummy",
    "LLM__GEMINI__API_KEY": "dummy",
    "LLM__GROQ__API_KEY": "dummy",
    "LLM__GATEWAY__API_KEY": "",  # JeV e Luna desligados por padrão nos testes
    "OBSERVABILITY__LANGSMITH_TRACING": "false",
}.items():
    os.environ.setdefault(_nome, _valor)

import pytest
from pydantic import SecretStr

from assessor_ai.settings import settings


@pytest.fixture(autouse=True)
def _sem_gateway(monkeypatch):
    """Teste nunca fala com o Vercel AI Gateway de verdade, mesmo com a chave no ambiente:
    quem testa o JeV liga com a chave fake e o HTTP stubado."""

    monkeypatch.setattr(settings.llm.gateway, "api_key", SecretStr(""))

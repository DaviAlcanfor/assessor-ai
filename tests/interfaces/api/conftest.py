import pytest
from fastapi.testclient import TestClient

from interfaces.api.main import app
from interfaces.api.rate_limiting import limiter


@pytest.fixture
def client():
    """
    Rate limit desligado — não é o que este pacote de testes cobre, e o
    `limiter` é um singleton em memória compartilhado entre testes.
    """

    limiter.enabled = False
    app.dependency_overrides.clear()

    yield TestClient(app)

    app.dependency_overrides.clear()
    limiter.enabled = True

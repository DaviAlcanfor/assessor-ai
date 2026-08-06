import pytest
from fastapi.testclient import TestClient
from guard import SecurityMiddleware

from interfaces.api.main import app
from interfaces.api.rate_limiting import limiter


@pytest.fixture
def client():
    """
    Rate limit e SecurityMiddleware (fastapi-guard) desligados — não é o que este pacote de
    testes cobre. O `limiter` é um singleton em memória compartilhado entre testes; o
    SecurityMiddleware bloqueia o host fake do TestClient ("testclient" não é um IP real), então
    precisa sair do stack (não dá pra só marcar "desabilitado" — ele não expõe esse toggle).
    """

    limiter.enabled = False
    app.dependency_overrides.clear()

    middleware_original = app.user_middleware
    app.user_middleware = [m for m in middleware_original if m.cls is not SecurityMiddleware]
    app.middleware_stack = None

    yield TestClient(app)

    app.dependency_overrides.clear()
    limiter.enabled = True
    app.user_middleware = middleware_original
    app.middleware_stack = None

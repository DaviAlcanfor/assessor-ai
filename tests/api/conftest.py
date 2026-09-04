from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient
from guard import SecurityMiddleware

from assessor_ai.api.app import app
from assessor_ai.api.limiter import limiter


@contextmanager
def _app_de_teste():
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

    yield app

    app.dependency_overrides.clear()
    limiter.enabled = True
    app.user_middleware = middleware_original
    app.middleware_stack = None


@pytest.fixture
def client():
    with _app_de_teste() as app_teste:
        yield TestClient(app_teste)


@pytest.fixture
def client_sem_reraise():
    """
    Igual ao `client`, mas deixa o handler genérico de `Exception` responder em vez de o
    TestClient relançar a exceção: é a única forma de assertar o 500 que o cliente real recebe.
    Use só nos testes que exercitam esse caminho — nos outros, relançar é o que dá o traceback.
    """

    with _app_de_teste() as app_teste:
        yield TestClient(app_teste, raise_server_exceptions=False)

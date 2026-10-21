from fastapi import FastAPI
from guard import SecurityMiddleware

from app.api.middleware.http_metrics import observar_http
from app.api.middleware.request_id import propagar_request_id
from app.api.middleware.security import security_config


def adicionar_middleware(app: FastAPI) -> None:
    # A ordem importa (o último registrado é o mais externo): o request_id fica por fora de tudo, pra
    # as métricas e o guard já logarem com ele.
    app.middleware("http")(observar_http)
    app.add_middleware(SecurityMiddleware, config=security_config())
    app.middleware("http")(propagar_request_id)


__all__ = ["adicionar_middleware", "observar_http", "propagar_request_id", "security_config"]

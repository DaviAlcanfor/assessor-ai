from starlette.datastructures import Headers
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from app.infra.context import session_context
from app.services import auth_service


class IdentidadeMCP:
    """Middleware ASGI do `/mcp`: autentica pelo `X-API-Key` e abre o `session_context()` em volta do
    request, pra toda tool rodar com o usuário dono da chave.

    Sem isso as tools não têm escopo e levantam `UsuarioDaSessaoNaoDefinido`: o MCP não passa pelo runner
    do grafo, que é quem abre o escopo no chat. Em modo dev (`API__KEY_AUTH_ENABLED=false`) o
    `auth_service` devolve o usuário padrão, como nas rotas HTTP.

    Depende de `stateless_http=True` no servidor: cada request carrega a própria identidade, sem sessão
    MCP guardada entre chamadas (que poderia ser reaproveitada por outro usuário).
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        api_key = Headers(scope=scope).get("x-api-key")
        user_id = await auth_service.usuario_da_chave(api_key)

        if user_id is None:
            resposta = JSONResponse({"detail": "Invalid API key"}, status_code=401)
            await resposta(scope, receive, send)
            return

        with session_context(user_id):
            await self.app(scope, receive, send)


__all__ = ["IdentidadeMCP"]

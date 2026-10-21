from importlib.metadata import version

from mcp.server.mcpserver import MCPServer
from mcp.server.transport_security import TransportSecuritySettings

from app.api.mcp.adapter import registrar_tools
from app.api.mcp.resources import registrar_resources
from app.graph.tools import AGENDA_TOOLS, FINANCEIRO_TOOLS, MERCADO_TOOLS
from app.settings import settings

_INSTRUCOES = (
    "Ferramentas do Assessor.AI para finanças pessoais (registrar e consultar transações, saldo), agenda "
    "(compromissos) e dados de mercado (cotação do dólar e outras moedas, PTAX, Selic, CDI, IPCA e "
    "simulação de juros compostos). Tudo opera sobre os dados do dono da API key enviada em X-API-Key. "
    "O resource categories://all lista as categorias válidas para `category_name`. Cotação e "
    "simulação são informativas: não são recomendação de investimento."
)


def criar_servidor() -> MCPServer:
    servidor = MCPServer(name="assessor-ai", version=version("assessor-ai"), instructions=_INSTRUCOES)

    registrar_tools(servidor, [*FINANCEIRO_TOOLS, *AGENDA_TOOLS, *MERCADO_TOOLS])
    registrar_resources(servidor)

    return servidor


servidor = criar_servidor()

# Instância única do sub-app ASGI: precisa ser a mesma no `app.mount()` e no lifespan que dispara o
# `session_manager.run()` dela (`lifespan.py`). `path="/"` porque a API já monta o sub-app em /mcp —
# o padrão ("/mcp") duplicaria pra /mcp/mcp. `stateless_http=True`: ver `auth.IdentidadeMCP`.
# `transport_security`: sem a lista de hosts o SDK só aceita `localhost:<porta>` e responde 421 a
# qualquer domínio de deploy (ver `API__MCP_ALLOWED_HOSTS`).
mcp_starlette = servidor.streamable_http_app(
    streamable_http_path="/",
    stateless_http=True,
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=settings.api.mcp_allowed_hosts,
        allowed_origins=settings.api.mcp_allowed_origins,
    ),
)


__all__ = ["criar_servidor", "mcp_starlette", "servidor"]

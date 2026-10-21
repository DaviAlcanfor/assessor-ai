"""MCP: autenticação por X-API-Key, escopo do usuário e schema das tools publicado."""

import json

import pytest
from langchain_core.tools import StructuredTool
from mcp.server.mcpserver import MCPServer
from pydantic import BaseModel, Field
from starlette.responses import PlainTextResponse
from starlette.testclient import TestClient

from app.api.mcp.adapter import registrar_tools
from app.api.mcp.annotations import (
    ESCRITA_DESTRUTIVA,
    LEITURA_EXTERNA,
    anotacao_da_tool,
)
from app.api.mcp.auth import IdentidadeMCP
from app.api.mcp.server import criar_servidor
from app.domain.errors import UsuarioDaSessaoNaoDefinido
from app.infra.context import current_user_id
from app.services import auth_service

USER = "22222222-2222-2222-2222-222222222222"


def _autenticar(monkeypatch, chaves: dict[str, str]):
    async def usuario_da_chave(api_key):
        return chaves.get(api_key) if api_key else None

    monkeypatch.setattr(auth_service, "usuario_da_chave", usuario_da_chave)


async def _app_interno(scope, receive, send):
    """Devolve o usuário que a tool enxergaria: prova que o escopo está aberto durante o request."""

    try:
        corpo = str(current_user_id())
    except UsuarioDaSessaoNaoDefinido:
        corpo = "sem-escopo"
    await PlainTextResponse(corpo)(scope, receive, send)


@pytest.fixture
def cliente():
    return TestClient(IdentidadeMCP(_app_interno))


def test_sem_api_key_devolve_401(cliente, monkeypatch):
    _autenticar(monkeypatch, {"chave-boa": USER})

    resposta = cliente.get("/")

    assert resposta.status_code == 401
    assert resposta.json() == {"detail": "Invalid API key"}


def test_api_key_invalida_devolve_401(cliente, monkeypatch):
    _autenticar(monkeypatch, {"chave-boa": USER})

    assert cliente.get("/", headers={"X-API-Key": "outra"}).status_code == 401


def test_api_key_valida_abre_o_escopo_do_usuario_dono_da_chave(cliente, monkeypatch):
    _autenticar(monkeypatch, {"chave-boa": USER})

    resposta = cliente.get("/", headers={"X-API-Key": "chave-boa"})

    assert resposta.status_code == 200
    assert resposta.text == USER


def test_o_escopo_nao_vaza_pro_proximo_request(cliente, monkeypatch):
    _autenticar(monkeypatch, {"chave-boa": USER})

    cliente.get("/", headers={"X-API-Key": "chave-boa"})

    with pytest.raises(UsuarioDaSessaoNaoDefinido):
        current_user_id()


class _ArgsExemplo(BaseModel):
    valor: float = Field(..., ge=0, description="Quantia em reais.")
    meses: int = Field(default=12, ge=1, le=600, description="Prazo em meses.")


def _tool_exemplo(chamadas: list[dict]) -> StructuredTool:
    def exemplo(valor: float, meses: int = 12) -> dict:
        chamadas.append({"valor": valor, "meses": meses, "usuario": str(current_user_id())})
        return {"status": "ok", "total": valor * meses}

    return StructuredTool.from_function(
        exemplo, name="simular_investimento", description="Simula.", args_schema=_ArgsExemplo
    )


async def test_adaptador_publica_o_schema_do_args_schema_com_descricoes_e_limites():
    servidor = MCPServer(name="teste")
    registrar_tools(servidor, [_tool_exemplo([])])

    [tool] = await servidor.list_tools()
    propriedades = tool.input_schema["properties"]

    assert tool.name == "simular_investimento"
    assert propriedades["valor"]["description"] == "Quantia em reais."
    assert propriedades["meses"]["maximum"] == 600
    assert tool.input_schema["required"] == ["valor"]  # `meses` tem default: opcional
    assert tool.annotations == LEITURA_EXTERNA


async def test_chamar_a_tool_pelo_mcp_roda_com_o_usuario_do_escopo():
    from app.infra.context import session_context

    chamadas: list[dict] = []
    servidor = MCPServer(name="teste")
    registrar_tools(servidor, [_tool_exemplo(chamadas)])

    with session_context(USER):
        resultado = await servidor.call_tool("simular_investimento", {"valor": 100, "meses": 3})

    assert chamadas == [{"valor": 100, "meses": 3, "usuario": USER}]
    assert json.loads(resultado.content[0].text)["total"] == 300  # type: ignore[union-attr]


async def test_servidor_real_expoe_as_tools_dos_tres_dominios_e_o_resource_de_categorias():
    servidor = criar_servidor()

    nomes = {t.name for t in await servidor.list_tools()}
    recursos = {str(r.uri) for r in await servidor.list_resources()}

    assert {"add_transaction", "total_balance", "add_event", "query_events"} <= nomes
    assert {"cotacao_atual", "ptax_dolar", "indicador_economico", "simular_investimento"} <= nomes
    assert recursos == {"categories://all"}


def test_tool_desconhecida_e_tratada_como_destrutiva():
    assert anotacao_da_tool("tool_que_ninguem_mapeou") == ESCRITA_DESTRUTIVA

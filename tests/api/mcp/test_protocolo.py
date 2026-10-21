"""O `/mcp` de ponta a ponta, falando o protocolo MCP de verdade (JSON-RPC sobre HTTP, stateless)."""

import json

import pytest
from starlette.testclient import TestClient

from app.api.mcp.auth import IdentidadeMCP
from app.api.mcp.server import mcp_starlette
from app.services import auth_service

USER = "22222222-2222-2222-2222-222222222222"
HEADERS = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def cliente():
    # O session manager do MCP só roda uma vez por instância: um cliente por módulo, não por teste.
    # A porta no host é exigida pela proteção contra DNS rebinding (`localhost:*`).
    with TestClient(IdentidadeMCP(mcp_starlette), base_url="http://localhost:8000") as c:
        yield c


@pytest.fixture(autouse=True)
def _chave_boa(monkeypatch):
    async def usuario_da_chave(api_key):
        return USER if api_key == "boa" else None

    monkeypatch.setattr(auth_service, "usuario_da_chave", usuario_da_chave)


def _rpc(cliente, metodo, params=None, chave="boa"):
    headers = HEADERS | ({"X-API-Key": chave} if chave else {})
    resposta = cliente.post(
        "/", headers=headers, json={"jsonrpc": "2.0", "id": 1, "method": metodo, "params": params or {}}
    )
    return resposta


def _resultado(resposta) -> dict:
    """A resposta vem como evento SSE (`data: {...}`)."""

    linha = next(l for l in resposta.text.splitlines() if l.startswith("data:"))
    return json.loads(linha.removeprefix("data:").strip())["result"]


def test_sem_chave_ou_com_chave_ruim_e_401(cliente):
    assert _rpc(cliente, "tools/list", chave=None).status_code == 401
    assert _rpc(cliente, "tools/list", chave="ruim").status_code == 401


def test_tools_list_publica_as_tools_com_descricao_e_anotacoes(cliente):
    tools = {t["name"]: t for t in _resultado(_rpc(cliente, "tools/list"))["tools"]}

    assert {"add_transaction", "add_event", "cotacao_atual", "simular_investimento"} <= set(tools)
    assert tools["simular_investimento"]["inputSchema"]["properties"]["meses"]["maximum"] == 600
    assert tools["simular_investimento"]["annotations"]["readOnlyHint"] is True
    assert tools["update_transaction"]["annotations"]["destructiveHint"] is True


def test_tools_call_executa_a_tool_de_verdade(cliente):
    # simular_investimento com taxa fixa é só conta: não depende de rede nem de banco
    argumentos = {"valor_inicial": 1000, "meses": 12, "taxa_anual_percentual": 12}

    resultado = _resultado(_rpc(cliente, "tools/call", {"name": "simular_investimento", "arguments": argumentos}))
    corpo = json.loads(resultado["content"][0]["text"])

    assert corpo["status"] == "ok"
    assert corpo["valor_final_bruto"] == 1120.0

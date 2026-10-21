"""Dicas (`ToolAnnotations`) que o cliente MCP usa pra decidir se pede confirmação ao usuário."""

from mcp.types import ToolAnnotations

LEITURA = ToolAnnotations(readOnlyHint=True, idempotentHint=True, openWorldHint=False)
# Leitura que sai pra internet (AwesomeAPI, Banco Central): mesmo efeito, mas `openWorld`.
LEITURA_EXTERNA = ToolAnnotations(readOnlyHint=True, idempotentHint=True, openWorldHint=True)
ESCRITA_ADITIVA = ToolAnnotations(
    readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False
)
ESCRITA_DESTRUTIVA = ToolAnnotations(
    readOnlyHint=False, destructiveHint=True, idempotentHint=True, openWorldHint=False
)

_POR_TOOL: dict[str, ToolAnnotations] = {
    # financeiro
    "add_transaction":     ESCRITA_ADITIVA,
    "update_transaction":  ESCRITA_DESTRUTIVA,
    "total_balance":       LEITURA,
    "daily_balance":       LEITURA,
    "query_transactions":  LEITURA,
    # agenda
    "add_event":           ESCRITA_ADITIVA,
    "update_event":        ESCRITA_DESTRUTIVA,
    "query_daily_events":  LEITURA,
    "query_events":        LEITURA,
    # mercado
    "cotacao_atual":        LEITURA_EXTERNA,
    "cotacao_historica":    LEITURA_EXTERNA,
    "ptax_dolar":           LEITURA_EXTERNA,
    "converter_moeda":      LEITURA_EXTERNA,
    "indicador_economico":  LEITURA_EXTERNA,
    "simular_investimento": LEITURA_EXTERNA,
}


def anotacao_da_tool(nome: str) -> ToolAnnotations:
    """Tool sem entrada na tabela é tratada como a mais perigosa: o cliente pede confirmação."""

    return _POR_TOOL.get(nome, ESCRITA_DESTRUTIVA)


__all__ = [
    "ESCRITA_ADITIVA",
    "ESCRITA_DESTRUTIVA",
    "LEITURA",
    "LEITURA_EXTERNA",
    "anotacao_da_tool",
]

import logging

from config.decorators import log_tool


@log_tool
def _tool_com_pii(cpf: str) -> dict:
    return {"status": "ok", "cpf_recebido": cpf}


def test_log_tool_nao_loga_pii_cru(caplog):
    with caplog.at_level(logging.INFO):
        _tool_com_pii(cpf="123.456.789-00")

    assert "123.456.789-00" not in caplog.text

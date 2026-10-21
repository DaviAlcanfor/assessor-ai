import re


def test_gera_request_id_quando_o_cliente_nao_manda(client):
    resposta = client.get("/health/live")

    assert re.fullmatch(r"[0-9a-f]{12}", resposta.headers["X-Request-ID"])


def test_devolve_o_request_id_enviado_pelo_cliente(client):
    resposta = client.get("/health/live", headers={"X-Request-ID": "req-abc_123.4"})

    assert resposta.headers["X-Request-ID"] == "req-abc_123.4"


def test_request_id_malformado_e_trocado_por_um_novo(client):
    # valor controlado pelo cliente vai pro log: nada de espaço, quebra de linha ou texto longo
    for ruim in ("tem espaco", "x" * 80, "a;b"):
        resposta = client.get("/health/live", headers={"X-Request-ID": ruim})

        assert resposta.headers["X-Request-ID"] != ruim
        assert re.fullmatch(r"[0-9a-f]{12}", resposta.headers["X-Request-ID"])

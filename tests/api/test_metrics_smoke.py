def test_metrics_endpoint_expoe_metrica_apos_request(client):
    client.get("/health/live")
    resposta = client.get("/metrics")

    assert resposta.status_code == 200
    corpo = resposta.text
    assert "assessor_http_requests_total" in corpo
    assert 'route="/health/live"' in corpo

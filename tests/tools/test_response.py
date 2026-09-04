from assessor_ai.graph.tools.response import Response


def test_ok_sem_argumentos():
    assert Response.ok() == {"status": "ok"}


def test_ok_com_argumentos_extras():
    resultado = Response.ok(total_records=3, transactions=[1, 2, 3])

    assert resultado == {
        "status": "ok",
        "total_records": 3,
        "transactions": [1, 2, 3],
    }


def test_error_com_string():
    assert Response.error("deu ruim") == {"status": "error", "message": "deu ruim"}


def test_error_com_exception():
    resultado = Response.error(ValueError("valor inválido"))

    assert resultado == {"status": "error", "message": "valor inválido"}

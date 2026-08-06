from interfaces.api.routes import health


def test_liveness_sempre_ok(client):
    resposta = client.get("/health/live")

    assert resposta.status_code == 200
    assert resposta.json() == {"status": "ok", "message": "service is running", "checks": None}


class _MongoOk:
    class client:
        class admin:
            @staticmethod
            def command(_cmd):
                return {"ok": 1}


def test_readiness_ok_quando_redis_e_mongo_respondem(client, monkeypatch):
    class RedisOk:
        def ping(self):
            return True

    monkeypatch.setattr(health, "get_client", lambda: RedisOk())
    monkeypatch.setattr(health, "banco", _MongoOk())

    resposta = client.get("/health/ready")

    assert resposta.status_code == 200
    assert resposta.json()["status"] == "ready"
    assert resposta.json()["checks"] == {"redis": True, "mongo": True}


def test_readiness_503_quando_redis_indisponivel(client, monkeypatch):
    class RedisDown:
        def ping(self):
            raise ConnectionError("redis fora do ar")

    monkeypatch.setattr(health, "get_client", lambda: RedisDown())
    monkeypatch.setattr(health, "banco", _MongoOk())

    resposta = client.get("/health/ready")

    assert resposta.status_code == 503
    assert resposta.json()["status"] == "unavailable"
    assert resposta.json()["checks"] == {"redis": False, "mongo": False}


def test_readiness_503_quando_mongo_indisponivel(client, monkeypatch):
    class RedisOk:
        def ping(self):
            return True

    class MongoDown:
        class client:
            class admin:
                @staticmethod
                def command(_cmd):
                    raise ConnectionError("mongo fora do ar")

    monkeypatch.setattr(health, "get_client", lambda: RedisOk())
    monkeypatch.setattr(health, "banco", MongoDown())

    resposta = client.get("/health/ready")

    assert resposta.status_code == 503
    assert resposta.json()["status"] == "unavailable"
    assert resposta.json()["checks"] == {"redis": True, "mongo": False}

class FakePipeline:
    def __init__(self, client):
        self._client = client
        self._ops = []

    def set(self, key, value, ex=None):
        self._ops.append((key, value, ex))
        return self

    def execute(self):
        for key, value, ex in self._ops:
            self._client.set(key, value, ex=ex)
        self._ops = []


class FakeRedis:
    """
    Stand-in mínimo para o cliente redis-py com decode_responses=True
    (mesma config de tools/redis/connection.py:get_client) — valores voltam
    como str, nunca bytes.
    """

    def __init__(self):
        self.store: dict[str, str] = {}
        self.ttls: dict[str, int] = {}

    def get(self, key):
        return self.store.get(key)

    def set(self, key, value, ex=None, nx=False):
        if nx and key in self.store:
            return None

        self.store[key] = value
        if ex is not None:
            self.ttls[key] = ex
        return True

    def delete(self, key):
        self.store.pop(key, None)
        self.ttls.pop(key, None)

    def exists(self, key):
        return int(key in self.store)

    def incr(self, key):
        self.store[key] = self.store.get(key, 0) + 1
        return self.store[key]

    def expire(self, key, seconds):
        self.ttls[key] = seconds
        return True

    def pipeline(self):
        return FakePipeline(self)

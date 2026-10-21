from app.domain.models.perfil import PerfilFinanceiroDocument
from app.repositories.perfil_repository import PerfilRepository


class _FakeCollection:
    def __init__(self):
        self.docs: dict[str, dict] = {}

    def find_one(self, filtro):
        return self.docs.get(filtro["user_id"])

    def update_one(self, filtro, update, upsert=False):
        user_id = filtro["user_id"]
        doc = self.docs.get(user_id)

        if doc is None:
            if not upsert:
                return
            doc = {"user_id": user_id}
            self.docs[user_id] = doc

        doc.update(update["$set"])


class _FakeMongoConn:
    def __init__(self):
        self._collection = _FakeCollection()

    def collection(self, _nome):
        return self._collection


class _FakePoint:
    def __init__(self, id, payload):
        self.id = id
        self.payload = payload


class _FakeQueryResult:
    def __init__(self, points):
        self.points = points


class _FakeQdrantClient:
    def __init__(self):
        self._collections: set[str] = set()
        self._pontos: dict[str, dict[str, dict]] = {}

    def collection_exists(self, name):
        return name in self._collections

    def create_collection(self, collection_name, vectors_config):
        self._collections.add(collection_name)
        self._pontos.setdefault(collection_name, {})

    def upsert(self, collection_name, points):
        for p in points:
            self._pontos[collection_name][p.id] = p.payload

    def delete(self, collection_name, points_selector):
        for pid in points_selector.points:
            self._pontos.get(collection_name, {}).pop(pid, None)

    def query_points(self, collection_name, query, query_filter=None, limit=1):
        candidatos = list(self._pontos.get(collection_name, {}).items())

        if query_filter is not None:
            for condicao in query_filter.must:
                candidatos = [
                    (pid, payload)
                    for pid, payload in candidatos
                    if payload.get(condicao.key) == condicao.match.value
                ]

        return _FakeQueryResult([_FakePoint(pid, payload) for pid, payload in candidatos[:limit]])


class _FakeEmbeddings:
    def embed_query(self, text):
        return [float(len(text))]


class _FakeQdrantConn:
    def __init__(self):
        self.client = _FakeQdrantClient()
        self.embeddings = _FakeEmbeddings()
        self.embeddings_documento = _FakeEmbeddings()


def _repo(monkeypatch=None):
    return PerfilRepository(conn=_FakeMongoConn(), qdrant_conn=_FakeQdrantConn())


def _documento(**overrides):
    dados = {
        "user_id": "user-1",
        "renda_mensal": 4200.0,
        "objetivo": "juntar para viagem",
        "tolerancia_risco": "baixa",
        "preferencias": "nao quero investimento agressivo",
    }
    dados.update(overrides)
    return PerfilFinanceiroDocument(**dados)


def test_salvar_grava_estruturado_e_indexa_preferencias(monkeypatch):
    repo = _repo(monkeypatch)

    registro = repo.salvar(_documento())

    assert registro == {
        "user_id": "user-1",
        "renda_mensal": 4200.0,
        "objetivo": "juntar para viagem",
        "tolerancia_risco": "baixa",
        "preferencias": "nao quero investimento agressivo",
    }

    doc = repo.collection.find_one({"user_id": "user-1"})
    assert doc["renda_mensal"] == 4200.0
    assert doc["tolerancia_risco"] == "baixa"

    pontos = repo.qdrant_conn.client._pontos["perfil_preferencias"]
    assert len(pontos) == 1
    assert next(iter(pontos.values()))["preferencias"] == "nao quero investimento agressivo"


def test_salvar_de_novo_substitui_nao_duplica(monkeypatch):
    repo = _repo(monkeypatch)

    repo.salvar(_documento(objetivo="objetivo antigo", preferencias="prefs antigas"))
    repo.salvar(_documento(objetivo="objetivo novo", preferencias="prefs novas"))

    assert len(repo.collection.docs) == 1
    assert repo.collection.docs["user-1"]["objetivo"] == "objetivo novo"

    pontos = repo.qdrant_conn.client._pontos["perfil_preferencias"]
    assert len(pontos) == 1
    assert next(iter(pontos.values()))["preferencias"] == "prefs novas"


def test_salvar_sem_preferencias_remove_ponto_antigo(monkeypatch):
    repo = _repo(monkeypatch)

    repo.salvar(_documento(preferencias="nao quero cripto"))
    assert len(repo.qdrant_conn.client._pontos["perfil_preferencias"]) == 1

    repo.salvar(_documento(preferencias=None))
    assert len(repo.qdrant_conn.client._pontos["perfil_preferencias"]) == 0


def test_buscar_devolve_cadastro_cru_por_user_id(monkeypatch):
    repo = _repo(monkeypatch)
    repo.salvar(_documento())

    assert repo.buscar("user-1")["objetivo"] == "juntar para viagem"
    assert repo.buscar("nao-existe") is None


def test_preferencias_relevantes_so_devolve_as_do_proprio_usuario():
    repo = _repo()
    repo.salvar(_documento(user_id="user-1", preferencias="restricao do user-1"))

    assert repo.preferencias_relevantes("user-1", "qualquer coisa") == ["restricao do user-1"]
    assert repo.preferencias_relevantes("user-2", "qualquer coisa") == []

"""Probe transport reuse must not cache dependency health or model metadata."""
from types import SimpleNamespace

from fastapi import Response

from app.config import Settings
from app.routes.health import readyz


def test_readiness_reuses_client_but_rechecks_model(monkeypatch):
    collection = SimpleNamespace(metadata={"embed_model": "nomic-embed-text"}, count=lambda: 3)
    registry = SimpleNamespace(metadata={"active_collection": "live-index"})
    names = []

    def get_collection(name):
        names.append(name)
        return registry if name.endswith("-registry") else collection

    client = SimpleNamespace(get_collection=get_collection)
    state = SimpleNamespace(settings=Settings(), retriever=SimpleNamespace(client=client),
                            redis=SimpleNamespace(ping=lambda: True))
    request = SimpleNamespace(app=SimpleNamespace(state=state))

    def unexpected_client(**kwargs):
        raise AssertionError("readiness must reuse the serving client")

    monkeypatch.setattr("app.routes.health.chromadb.HttpClient", unexpected_client)
    response = Response()
    assert readyz(request, response)["status"] == "ready"
    collection.metadata = {"embed_model": "different-model"}
    response = Response()
    assert readyz(request, response)["status"] == "not_ready"
    assert response.status_code == 503
    assert names == ["rahbar-registry", "live-index"] * 2

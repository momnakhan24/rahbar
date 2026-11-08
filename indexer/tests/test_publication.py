"""Publication must be atomic and independent of API-only Redis access."""
from types import SimpleNamespace

import pytest

from pipeline.config import get_settings
from pipeline.models import Chunk
from pipeline.store import store


@pytest.mark.parametrize("write_fails", [False, True])
def test_registry_switches_only_after_successful_writes(monkeypatch, write_fails) -> None:
    registry = SimpleNamespace(metadata={"active_collection": "old"})

    def modify(metadata):
        registry.metadata = metadata

    def add(**kwargs):
        if write_fails:
            raise RuntimeError("simulated batch failure")

    registry.modify = modify
    client = SimpleNamespace(
        create_collection=lambda **kwargs: SimpleNamespace(add=add),
        get_or_create_collection=lambda name: registry,
    )
    monkeypatch.setattr("pipeline.store.get_client", lambda settings: client)
    monkeypatch.setenv("REDIS_URL", "redis://unreachable.invalid:6379/0")
    item = Chunk("c1", "policy evidence", "rules.md", "1", 1, "2026", False)
    if write_fails:
        with pytest.raises(RuntimeError, match="batch failure"):
            store([item], [[0.1, 0.2]], get_settings())
        assert registry.metadata == {"active_collection": "old"}
    else:
        assert store([item], [[0.1, 0.2]], get_settings()) == 1
        assert registry.metadata["active_collection"] != "old"
        assert registry.metadata["dimension"] == 2

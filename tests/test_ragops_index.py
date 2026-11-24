import httpx

from ragops import index as ragops_index
from ragops.index import synchronize
from ragops.lake import Lake
from ragops.verify import Source


class Collection:
    def __init__(self):
        self.rows = {}

    def get(self, limit=None, offset=0, include=(), ids=None):
        selected = list(self.rows)[offset:offset + limit] if ids is None else ids
        return {"ids": selected} | {
            field: [self.rows[item][field] for item in selected] for field in include
        }

    def upsert(self, ids, **fields):
        for index, item in enumerate(ids):
            self.rows[item] = {field: values[index] for field, values in fields.items()}

    def delete(self, ids):
        for item in ids:
            del self.rows[item]


def test_index_reconciles_update_delete_and_restore(tmp_path):
    lake = Lake(tmp_path)
    collection = Collection()

    def embed(texts):
        return [[1.0, 0.0] for _ in texts]

    for version, days in (("1", "three"), ("2", "five")):
        text = f"Borrowed library recorders are due back in {days} working days."
        source = Source("loans", "loans.md", "Equipment loans", version, 1, "public", (text,))
        lake.admit(source, text.encode(), ".md", "test", embed, 0.95, 20)
        assert synchronize(collection, lake, embed, 400, 50)["chunks_embedded"] == 1
        assert len(collection.rows) == 1
        assert next(iter(collection.rows.values()))["metadatas"]["doc_version"] == version
        assert synchronize(collection, lake, embed, 400, 50)["chunks_embedded"] == 0
    lake.delete("loans")
    assert synchronize(collection, lake, embed, 400, 50)["inactive_doc_chunk_counts"] == {"loans": 0}
    assert not collection.rows
    lake.restore("loans", "1")
    assert synchronize(collection, lake, embed, 400, 50)["orphan_check"] == "pass"
    assert "three" in next(iter(collection.rows.values()))["documents"]
    fork = Collection()
    counts = synchronize(fork, lake, embed, 600, 50, reuse=collection)
    assert counts["chunks_embedded"] == 0
    assert counts["chunks_reused"] == 1


def test_index_retries_transient_transport_errors(monkeypatch):
    attempts = []

    def write(ids):
        attempts.append(ids)
        if len(attempts) == 1:
            raise httpx.ConnectError("temporary DNS failure")

    monkeypatch.setattr(ragops_index, "sleep", lambda _: None)
    ragops_index.write_with_retry(write, ids=["a"])
    assert attempts == [["a"], ["a"]]

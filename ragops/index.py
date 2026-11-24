"""Reconcile one Chroma collection from the active lake manifest."""

from __future__ import annotations

import hashlib
from collections import Counter
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from time import sleep
from typing import Any

import httpx

from indexer.pipeline.chunk import chunk
from indexer.pipeline.clean import clean
from indexer.pipeline.models import Document, Page

from .lake import Lake
from .verify import Embed


@dataclass(frozen=True)
class IndexedChunk:
    id: str
    text: str
    metadata: dict[str, str | int | bool]


def chunks(lake: Lake, size: int, overlap: int) -> Iterator[IndexedChunk]:
    for doc_id, version in sorted(lake.manifest["active"].items()):
        stored = lake.manifest["versions"][doc_id][version]["document"]
        pages = [Page(stored["source"], n, text) for n, text in enumerate(stored["pages"], 1)]
        document = clean(Document(stored["source"], version, False, pages))
        for item in chunk(document, size, overlap):
            chunk_id = hashlib.sha256(f"{doc_id}\0{item.id}".encode()).hexdigest()
            yield IndexedChunk(chunk_id, item.text, item.metadata() | {
                "doc_id": doc_id, "access": stored["access"], "status": "active",
                "chunk_hash": hashlib.sha256(item.text.encode()).hexdigest(),
            })


def rows(collection: Any, include: list[str]) -> Iterator[dict[str, Any]]:
    offset = 0
    while True:
        page = collection.get(limit=256, offset=offset, include=include)
        for index, chunk_id in enumerate(page["ids"]):
            yield {"id": chunk_id} | {field: page[field][index] for field in include}
        offset += len(page["ids"])
        if len(page["ids"]) < 256:
            return


def write_with_retry(operation: Callable[..., Any], **parameters: Any) -> None:
    """Replay idempotent writes when a rolling backend restart interrupts transport."""
    delays = (1, 3, 8, 16, 32)
    for delay in delays:
        try:
            operation(**parameters)
            return
        except httpx.TransportError:
            sleep(delay)
    operation(**parameters)


def synchronize(
    collection: Any, lake: Lake, embed: Embed, size: int, overlap: int, *, reuse: Any = None,
) -> dict[str, Any]:
    expected = {item.id: item for item in chunks(lake, size, overlap)}
    indexed = {row["id"]: row for row in rows(collection, ["metadatas"])}
    upserts = [
        item for item in expected.values()
        if item.id not in indexed or item.metadata != indexed[item.id]["metadatas"]
    ]
    deleted = sorted(indexed.keys() - expected.keys())
    reusable = {
        row["metadatas"]["chunk_hash"]: row["id"] for row in rows(reuse, ["metadatas"])
    } if reuse is not None else {}
    embedded = 0
    reused = 0
    for start in range(0, len(upserts), 16):
        batch = upserts[start:start + 16]
        existing_ids = [
            item.id for item in batch
            if item.id in indexed
            and item.metadata["chunk_hash"] == indexed[item.id]["metadatas"].get("chunk_hash")
        ]
        existing = collection.get(ids=existing_ids, include=["embeddings"]) if existing_ids else None
        vectors = {
            chunk_id: vector.tolist() if hasattr(vector, "tolist") else vector
            for chunk_id, vector in zip(existing["ids"], existing["embeddings"], strict=True)
        } if existing is not None else {}
        shared = {
            item.id: reusable[item.metadata["chunk_hash"]]
            for item in batch if item.id not in vectors and item.metadata["chunk_hash"] in reusable
        }
        if shared:
            prior = reuse.get(ids=sorted(set(shared.values())), include=["embeddings"])
            shared_vectors = {
                chunk_id: vector.tolist() if hasattr(vector, "tolist") else vector
                for chunk_id, vector in zip(prior["ids"], prior["embeddings"], strict=True)
            }
            for chunk_id, prior_id in shared.items():
                vectors[chunk_id] = shared_vectors[prior_id]
            reused += len(shared)
        missing = [item for item in batch if item.id not in vectors]
        if missing:
            vectors.update(zip(
                (item.id for item in missing), embed([item.text for item in missing]), strict=True,
            ))
        embedded += len(missing)
        write_with_retry(
            collection.upsert,
            ids=[item.id for item in batch],
            documents=[item.text for item in batch],
            metadatas=[item.metadata for item in batch],
            embeddings=[vectors[item.id] for item in batch],
        )
    for start in range(0, len(deleted), 256):
        write_with_retry(collection.delete, ids=deleted[start:start + 256])

    final = {row["id"]: row["metadatas"] for row in rows(collection, ["metadatas"])}
    if set(final) != set(expected) or any(final[item.id] != item.metadata for item in expected.values()):
        raise RuntimeError("index reconciliation left missing, stale, or orphaned chunks")
    inactive = sorted(
        set(lake.manifest["versions"]) - set(lake.manifest["active"])
    )
    counts_by_document = Counter(metadata["doc_id"] for metadata in final.values())
    return {
        "chunks_embedded": embedded, "chunks_deleted": len(deleted),
        "chunks_kept": len(expected) - embedded - reused, "chunks_reused": reused,
        "orphan_check": "pass",
        "inactive_doc_chunk_counts": {doc_id: counts_by_document[doc_id] for doc_id in inactive},
    }

"""Incrementally replace named sources through the same atomic publication path.

Run as the sole indexer Job, never in an API process. Unchanged source vectors are
copied from the published index; changed sources execute all five pipeline stages.
"""
from __future__ import annotations

import argparse

from .chunk import chunk
from .clean import clean
from .config import IndexerSettings, get_settings
from .embed import embed
from .extract import extract
from .models import Chunk
from .run import discover, log
from .store import get_client, store


def refresh_sources(settings: IndexerSettings, sources: list[str]) -> int:
    requested = set(sources)
    found = {p.name: (p, version, superseded)
             for p, version, superseded in discover(settings.corpus_dir)}
    if not requested or requested - found.keys():
        raise ValueError("refresh requires existing corpus source names")
    client = get_client(settings)
    registry_name = f"{settings.collection[:40]}-registry"
    registry = client.get_collection(registry_name)
    active = registry.metadata["active_collection"]
    current = client.get_collection(active)
    metadata = current.metadata or {}
    if metadata.get("embed_model") != settings.embed_model:
        raise ValueError("cannot reuse vectors from a different embedding model")
    data = current.get(include=["documents", "metadatas", "embeddings"])
    pieces: list[Chunk] = []
    vectors: list[list[float]] = []
    for identifier, text, meta, vector in zip(data["ids"], data["documents"],
                                               data["metadatas"], data["embeddings"]):
        if meta["source"] not in requested:
            pieces.append(Chunk(identifier, text, meta["source"], meta["section"],
                                meta["page"], meta["doc_version"], meta["superseded"]))
            vectors.append([float(value) for value in vector])
    replacements: list[Chunk] = []
    for source in sorted(requested):
        path, version, superseded = found[source]
        document = clean(extract(str(path), version, superseded))
        changed = chunk(document, settings.chunk_size, settings.chunk_overlap)
        if not changed:
            raise ValueError(f"refusing empty replacement for source: {source}")
        replacements.extend(changed)
        log("source refreshed", source=source, chunks=len(changed),
            sections=sorted({p.section for p in changed}))
    replacement_vectors = embed([p.text for p in replacements], settings)
    if client.get_collection(registry_name).metadata["active_collection"] != active:
        raise RuntimeError("active index changed during refresh; refusing stale publication")
    log("refresh prepared", reused_chunks=len(pieces), replaced_sources=sorted(requested),
        new_chunks=len(replacements), previous_collection=active)
    return store(pieces + replacements, vectors + replacement_vectors, settings)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sources", nargs="+", required=True)
    args = parser.parse_args()
    count = refresh_sources(get_settings(), args.sources)
    log("refresh finished", chunks=count)


if __name__ == "__main__":
    main()

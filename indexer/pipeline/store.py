"""Stage 5: Store. The only code in the whole system that writes to Chroma."""

from __future__ import annotations

import time
import uuid
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen

from .config import IndexerSettings
from .models import Chunk


def get_client(settings: IndexerSettings) -> Any:
    import chromadb  # the thin client, from chromadb-client in requirements.txt
    from chromadb.config import Settings as ChromaSettings

    # Jobs can start before the Chroma server is accepting requests.
    heartbeat = f"http://{settings.chroma_host}:{settings.chroma_port}/api/v2/heartbeat"
    deadline = time.monotonic() + 60
    while True:
        try:
            with urlopen(heartbeat, timeout=2) as response:
                response.read()
            break
        except (URLError, TimeoutError):
            if time.monotonic() >= deadline:
                raise
            time.sleep(2)

    return chromadb.HttpClient(host=settings.chroma_host, port=settings.chroma_port,
                               settings=ChromaSettings(anonymized_telemetry=False))


def store(chunks: list[Chunk], vectors: list[list[float]], settings: IndexerSettings) -> int:
    """Write every chunk with its vector and metadata, and record the embedding model
    and vector dimension in the collection metadata (section 4.4). Return the count."""
    if len(chunks) != len(vectors):
        raise ValueError("each chunk must have exactly one embedding")
    if not chunks:
        raise ValueError("refusing to replace the active index with an empty corpus")
    dimensions = {len(vector) for vector in vectors}
    if len(dimensions) != 1 or not next(iter(dimensions)):
        raise ValueError("embedding vectors have inconsistent dimensions")

    client = get_client(settings)
    dimension = next(iter(dimensions))
    revision = f"{int(time.time())}-{uuid.uuid4().hex[:8]}"
    physical_name = f"{settings.collection[:36]}-{revision}"
    collection = client.create_collection(
        name=physical_name,
        metadata={
            "hnsw:space": "cosine",
            "embed_model": settings.embed_model,
            "dimension": dimension,
            "index_revision": revision,
            "logical_collection": settings.collection,
        },
    )
    batch_size = 256
    for start in range(0, len(chunks), batch_size):
        batch_chunks = chunks[start:start + batch_size]
        batch_vectors = vectors[start:start + batch_size]
        collection.add(
            ids=[item.id for item in batch_chunks],
            documents=[item.text for item in batch_chunks],
            embeddings=batch_vectors,
            metadatas=[item.metadata() for item in batch_chunks],
        )

    # Publish only after every batch is stored. Readers keep using the previous
    # collection if extraction or embedding fails partway through the new build.
    registry_name = f"{settings.collection[:40]}-registry"
    registry = client.get_or_create_collection(name=registry_name)
    registry.modify(metadata={
        "active_collection": physical_name,
        "embed_model": settings.embed_model,
        "dimension": dimension,
        "index_revision": revision,
    })

    # Publishing a new revision invalidates old cache keys immediately. The API
    # prunes obsolete revisions on its next lookup; only it may connect to Redis.
    return len(chunks)

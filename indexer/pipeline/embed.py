"""Stage 4: Embed. One vector per chunk, from the pinned model only."""

from __future__ import annotations

import httpx

from .config import IndexerSettings


def embed(texts: list[str], settings: IndexerSettings) -> list[list[float]]:
    """Embed with settings.embed_model and nothing else.

    With Ollama: POST {ollama_url}/api/embed with {"model": ..., "input": [texts]}
    returns {"embeddings": [[...], ...]}. Batch the calls; one request per chunk is slow.
    """
    if not texts:
        return []
    vectors: list[list[float]] = []
    batch_size = 64
    with httpx.Client(timeout=httpx.Timeout(180.0, connect=15.0)) as client:
        for start in range(0, len(texts), batch_size):
            batch = texts[start:start + batch_size]
            response = client.post(
                f"{settings.ollama_url.rstrip('/')}/api/embed",
                json={"model": settings.embed_model, "input": batch},
            )
            response.raise_for_status()
            payload = response.json()
            batch_vectors = payload.get("embeddings")
            if not batch_vectors and len(batch) == 1 and payload.get("embedding"):
                batch_vectors = [payload["embedding"]]
            if not batch_vectors or len(batch_vectors) != len(batch):
                raise ValueError("embedding provider returned an unexpected vector count")
            vectors.extend([[float(value) for value in vector] for vector in batch_vectors])
    dimensions = {len(vector) for vector in vectors}
    if len(dimensions) != 1 or not next(iter(dimensions)):
        raise ValueError("embedding provider returned inconsistent vector dimensions")
    return vectors

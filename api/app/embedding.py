"""Embedding calls shared by Chroma retrieval and the semantic cache."""

from __future__ import annotations

import httpx

from .config import Settings


def embed_query(text: str, settings: Settings) -> list[float]:
    """Embed a query through the pinned Ollama model used by the indexer."""
    response = httpx.post(
        f"{settings.ollama_url.rstrip('/')}/api/embed",
        json={"model": settings.embed_model, "input": text},
        timeout=60.0,
    )
    response.raise_for_status()
    payload = response.json()
    vectors = payload.get("embeddings")
    if not vectors and payload.get("embedding"):
        vectors = [payload["embedding"]]
    if not vectors or not vectors[0]:
        raise ValueError("embedding provider returned no vector")
    return [float(value) for value in vectors[0]]

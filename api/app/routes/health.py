"""Liveness and readiness (section 4.3). They answer different questions."""

from __future__ import annotations

import logging

import chromadb
from fastapi import APIRouter, Request, Response
from chromadb.config import Settings as ChromaSettings

router = APIRouter()
log = logging.getLogger("rahbar.health")


def embedding_model_mismatch(indexed: str | None, configured: str) -> bool:
    """Fail readiness if query and collection vectors were built by different models."""
    return indexed != configured


@router.get("/healthz")
def healthz() -> dict[str, str]:
    """Is the process alive? Must never touch Chroma, Redis or the LLM."""
    return {"status": "alive"}


@router.get("/readyz")
def readyz(request: Request, response: Response) -> dict[str, object]:
    settings = request.app.state.settings
    checks: dict[str, object] = {}
    try:
        # Reuse the serving client's connection pool. Constructing a thin client
        # on every probe repeatedly allocates transport/telemetry resources.
        client = getattr(request.app.state, "health_chroma", None)
        if client is None:
            client = getattr(request.app.state.retriever, "client", None)
            if client is None:
                client = chromadb.HttpClient(
                    host=settings.chroma_host,
                    port=settings.chroma_port,
                    settings=ChromaSettings(anonymized_telemetry=False),
                )
            request.app.state.health_chroma = client
        registry_name = f"{settings.collection[:40]}-registry"
        try:
            registry = client.get_collection(registry_name)
            active = (registry.metadata or {}).get("active_collection")
        except Exception:
            active = None
        collection = client.get_collection(str(active)) if active else client.get_collection(settings.collection)
        count = collection.count()
        checks["chroma"] = {"ok": count > 0, "count": count}
        indexed_model = (collection.metadata or {}).get("embed_model")
        mismatch = embedding_model_mismatch(indexed_model, settings.embed_model)
        matches = not mismatch
        checks["embedding_model"] = {
            "ok": matches,
            "indexed": indexed_model,
            "configured": settings.embed_model,
        }
        if not matches:
            log.error("embedding model conflict", extra={
                "indexed_model": indexed_model, "configured_model": settings.embed_model,
            })
    except Exception as exc:
        checks["chroma"] = {"ok": False, "error": type(exc).__name__}
        checks["embedding_model"] = {"ok": False, "error": "Chroma collection unavailable"}
    try:
        request.app.state.redis.ping()
        checks["redis"] = {"ok": True}
    except Exception as exc:
        checks["redis"] = {"ok": False, "error": type(exc).__name__}
    ready = all(isinstance(item, dict) and item.get("ok") for item in checks.values())
    if not ready:
        response.status_code = 503
    return {"status": "ready" if ready else "not_ready", "checks": checks}

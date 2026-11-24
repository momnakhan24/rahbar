"""Read-only RAGOps serving entry point using the Assignment 02 generator."""

from __future__ import annotations

import os
from collections import OrderedDict
from dataclasses import replace
from datetime import datetime, timezone
from threading import Lock
from time import perf_counter
from typing import Any
from uuid import uuid4

import httpx
from fastapi import FastAPI, HTTPException

from api.app import config as api_config
from api.app.providers.llm.ollama import OllamaProvider
from api.app.schemas import AskRequest, Passage
from indexer.pipeline.config import get_settings
from indexer.pipeline.embed import embed
from indexer.pipeline.store import get_client

from .tracing import append_trace, prompt_hash, summarize, trace_path
from .verify import INSTRUCTION

app = FastAPI(title="RAHBAR RAGOps")
_CACHE: OrderedDict[tuple[str, str, str], dict[str, Any]] = OrderedDict()
_CACHE_LOCK = Lock()


def query(
    question: str, collection: Any, settings: Any, *, bypass_cache: bool = False,
    retrieval_only: bool = False,
) -> dict[str, Any]:
    started = perf_counter()
    settings_api = replace(
        api_config.get_settings(), temperature=0.0,
        ollama_url=os.getenv("LLM_OLLAMA_URL", settings.ollama_url),
    )
    version = os.environ["EMBEDDING_VERSION"]
    top_k = settings_api.top_k
    filters = {"$and": [{"status": "active"}, {"access": "public"}]}
    revision = str(collection.metadata.get("lake_revision", "unpublished"))
    key = (settings.collection, revision, question)
    phases = dict.fromkeys(("embed", "retrieve", "rerank", "rail", "generate"), 0.0)
    with _CACHE_LOCK:
        cached = None if bypass_cache or retrieval_only else _CACHE.get(key)
        if cached is not None:
            _CACHE.move_to_end(key)
    if cached is None:
        start = perf_counter()
        vector = embed([question], settings)[0]
        phases["embed"] = (perf_counter() - start) * 1000
        start = perf_counter()
        hits = collection.query(
            query_embeddings=[vector], n_results=top_k, where=filters,
            include=["documents", "metadatas", "distances"],
        )
        phases["retrieve"] = (perf_counter() - start) * 1000
        start = perf_counter()
        retrieved = sorted(
            (
                {"chunk_id": chunk_id, "text": text, "score": 1 - distance} | meta
                for chunk_id, text, meta, distance in zip(
                    hits["ids"][0], hits["documents"][0], hits["metadatas"][0],
                    hits["distances"][0], strict=True,
                )
            ),
            key=lambda row: (-row["score"], row["chunk_id"]),
        )
        phases["rerank"] = (perf_counter() - start) * 1000
        start = perf_counter()
        actions = []
        context = []
        for row in retrieved:
            match = INSTRUCTION.search(row["text"])
            if match:
                actions.append({
                    "rail": "retrieval", "chunk_id": row["chunk_id"], "doc_id": row["doc_id"],
                    "action": "drop", "pattern": match.re.pattern, "matched_text": match.group(),
                })
            elif row["score"] >= settings_api.relevance_floor:
                context.append(row)
        phases["rail"] = (perf_counter() - start) * 1000
        requests: list[dict[str, Any]] = []
        start = perf_counter()
        generation_errors = []
        response = {
            "answer": "The available documents do not establish an answer to this question.",
            "answered_from_context": False, "confidence": "low", "citations": [],
        }
        if context and not retrieval_only:
            provider = OllamaProvider(settings_api, record_request=requests.append)
            passages = [Passage.model_validate(row) for row in context]
            for _ in range(2):
                try:
                    answer = provider.generate_extractive(question, passages)
                except (ValueError, KeyError, TypeError) as error:
                    generation_errors.append(type(error).__name__)
                else:
                    response = answer.model_dump(exclude={"reasoning"})
                    break
        phases["generate"] = (perf_counter() - start) * 1000
        computed = {
            "retrieved": retrieved, "context": context, "guardrail_actions": actions,
            "response": response, "model_requests": requests, "prompt_hash": prompt_hash(requests),
            "reranked_order": [row["chunk_id"] for row in retrieved],
            "generation_errors": generation_errors,
        }
        if response["answered_from_context"] and not bypass_cache and revision != "unpublished":
            with _CACHE_LOCK:
                _CACHE[key] = computed
                _CACHE.move_to_end(key)
                if len(_CACHE) > 128:
                    _CACHE.popitem(last=False)
    else:
        computed = cached
    trace = computed | {
        "trace_id": uuid4().hex, "timestamp": datetime.now(timezone.utc).isoformat(),
        "user_query": question, "rewritten_query": question,
        "embedding_model": settings.embed_model, "embedding_version": version,
        "collection": settings.collection, "collection_revision": revision, "filters": filters,
        "model": settings_api.llm_model,
        "params": {"temperature": 0.0, "seed": 0, "top_k": top_k,
                   "relevance_floor": settings_api.relevance_floor},
        "citations": computed["response"]["citations"],
        "latency_ms": phases | {"total": (perf_counter() - started) * 1000},
        "cache": "miss" if cached is None else "hit",
        "retrieval_only": retrieval_only,
    }
    append_trace(trace_path(), trace)
    return trace


@app.get("/healthz")
def health() -> dict[str, str]:
    return {"status": "ok"}


def get_collection(settings: Any) -> Any:
    collection = get_client(settings).get_collection(settings.collection)
    metadata = collection.metadata or {}
    if metadata.get("embed_model") != settings.embed_model:
        raise HTTPException(status_code=503, detail="collection embedding model mismatch")
    return collection


@app.get("/readyz")
def ready() -> dict[str, str]:
    try:
        get_collection(get_settings())
    except (OSError, ValueError, RuntimeError) as error:
        raise HTTPException(status_code=503, detail="collection unavailable") from error
    return {"status": "ready"}


@app.post("/query")
def ask(payload: AskRequest, bypass_cache: bool = False, retrieval_only: bool = False) -> dict[str, Any]:
    settings = get_settings()
    try:
        return query(
            payload.question, get_collection(settings), settings,
            bypass_cache=bypass_cache, retrieval_only=retrieval_only,
        )
    except (httpx.HTTPError, ValueError) as error:
        raise HTTPException(status_code=502, detail="pipeline could not complete the query") from error


@app.get("/metrics")
def metrics() -> dict[str, Any]:
    return summarize(trace_path(), 24)

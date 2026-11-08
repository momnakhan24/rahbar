"""Prometheus metrics at /metrics (section 4.8).

Request count and latency are wired up already. Add your own the same way:
retrieval latency, generation latency, cache hits, abstentions, fallbacks, tokens.
"""

from __future__ import annotations

from fastapi import APIRouter, Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

router = APIRouter()

REQUESTS = Counter("rahbar_requests_total", "HTTP requests", ["path", "status"])
LATENCY = Histogram(
    "rahbar_request_seconds",
    "HTTP request latency",
    ["path"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10, 30, 60),
)
RETRIEVAL_LATENCY = Histogram("rahbar_retrieval_seconds", "Vector retrieval latency")
GENERATION_LATENCY = Histogram("rahbar_generation_seconds", "LLM generation latency")
CACHE_CHECKS = Counter("rahbar_cache_checks_total", "Semantic cache lookups")
CACHE_HITS = Counter("rahbar_cache_hits_total", "Semantic cache hits")
CACHE_HIT_RATIO = Gauge("rahbar_cache_hit_ratio", "Observed semantic cache hit ratio")
ABSTENTIONS = Counter("rahbar_abstentions_total", "Answers declined for insufficient context")
FALLBACKS = Counter("rahbar_fallbacks_total", "Safe answer fallbacks after provider failures")
TOKENS_IN = Counter("rahbar_tokens_in_total", "Estimated input tokens processed")
TOKENS_OUT = Counter("rahbar_tokens_out_total", "Estimated output tokens generated")


def observe_cache(hit: bool) -> None:
    CACHE_CHECKS.inc()
    if hit:
        CACHE_HITS.inc()
    checks = CACHE_CHECKS._value.get()
    CACHE_HIT_RATIO.set(CACHE_HITS._value.get() / checks if checks else 0.0)


@router.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

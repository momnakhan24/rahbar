"""Append portable traces and reconstruct the exact model requests."""

from __future__ import annotations

import hashlib
import json
import math
import os
from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


def prompt_hash(requests: list[dict[str, Any]]) -> str:
    canonical = json.dumps(requests, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def append_trace(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, ensure_ascii=False, separators=(",", ":"))
    with path.open("ab", buffering=0) as handle:
        handle.write((line + "\n").encode("utf-8"))
    print(line, flush=True)


def records(path: Path) -> Iterator[dict[str, Any]]:
    if path.exists():
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.endswith("\n"):
                    yield json.loads(line)


def reconstruct(path: Path, trace_id: str) -> dict[str, Any]:
    for record in records(path):
        if record["trace_id"] == trace_id:
            if record["prompt_hash"] != prompt_hash(record["model_requests"]):
                raise ValueError("stored model requests failed hash verification")
            return {
                "trace_id": trace_id, "prompt_hash": record["prompt_hash"],
                "context": record["context"], "model_requests": record["model_requests"],
            }
    raise ValueError(f"no trace matches {trace_id}")


def percentile(values: list[float], quantile: float) -> float | None:
    return sorted(values)[math.ceil(quantile * len(values)) - 1] if values else None


def summarize(path: Path, hours: float) -> dict[str, Any]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    traces = [
        row for row in records(path)
        if not row.get("retrieval_only") and datetime.fromisoformat(row["timestamp"]) >= cutoff
    ]
    count = len(traces)
    scores = [trace["retrieved"][0]["score"] for trace in traces if trace["retrieved"]]
    bounds = (0.0, 0.25, 0.5, 0.75, 1.0)
    return {
        "count": count,
        "top1_similarity_histogram": {
            str(bound): sum(score <= bound for score in scores) for bound in bounds
        },
        "top1_similarity_samples": len(scores),
        "abstention_rate": sum(not row["response"]["answered_from_context"] for row in traces) / count
        if count else None,
        "cache_hit_rate": sum(row["cache"] == "hit" for row in traces) / count if count else None,
        "injection_flagged_count": sum(len(row["guardrail_actions"]) for row in traces),
        "p95_latency_ms": {
            stage: percentile([row["latency_ms"][stage] for row in traces], 0.95)
            for stage in ("embed", "retrieve", "rerank", "rail", "generate", "total")
        },
    }


def trace_path() -> Path:
    return Path(os.environ.get("TRACE_PATH", "/data/traces/traces.jsonl"))

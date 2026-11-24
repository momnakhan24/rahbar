"""Measure the distance from live queries to existing offline test cases."""

from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from indexer.pipeline.config import get_settings
from indexer.pipeline.embed import embed

from .evaluation import json_lines
from .lake import write_json
from .verify import cosine


def coverage(live_path: Path, golden_path: Path, threshold: float, out: Path) -> dict[str, Any]:
    live, golden = json_lines(live_path), json_lines(golden_path)
    if not live or not golden or not 0 <= threshold <= 1:
        raise ValueError("coverage needs nonempty query sets and a threshold within [0, 1]")
    settings = get_settings()
    gold_vectors = embed([row["question"] for row in golden], settings)
    live_vectors = embed([row["question"] for row in live], settings)
    matches = []
    clusters: list[dict[str, Any]] = []
    for item, vector in zip(live, live_vectors, strict=True):
        index, score = max(
            enumerate(cosine(vector, candidate) for candidate in gold_vectors),
            key=lambda pair: pair[1],
        )
        row = item | {"best_id": golden[index]["id"], "cosine": score, "covered": score >= threshold}
        matches.append(row)
        if row["covered"]:
            continue
        nearest = max(clusters, key=lambda cluster: cosine(vector, cluster["representative"]), default=None)
        if nearest and cosine(vector, nearest["representative"]) >= threshold:
            nearest["queries"].append(item["question"])
        else:
            clusters.append({
                "label": item.get("topic", item["question"]),
                "representative": vector, "queries": [item["question"]],
            })
    now = datetime.now(timezone.utc)
    result = {
        "threshold": threshold, "coverage": sum(row["covered"] for row in matches) / len(matches),
        "environment": {
            "timestamp": now.isoformat(),
            "embedding_model": settings.embed_model,
            "embedding_version": os.getenv("EMBEDDING_VERSION"),
            "live_sha256": hashlib.sha256(live_path.read_bytes()).hexdigest(),
            "golden_sha256": hashlib.sha256(golden_path.read_bytes()).hexdigest(),
        },
        "queries": matches,
        "uncovered_topics": [{"label": row["label"], "queries": row["queries"]} for row in clusters],
    }
    stamp = now.strftime("%Y%m%dT%H%M%S%fZ")
    output = out / f"coverage_{stamp}.json"
    write_json(output, result)
    print(f"Coverage: {result['coverage']:.2%} at cosine {threshold:.3f} ({output})")
    for cluster in result["uncovered_topics"]:
        print(f"{cluster['label']}: {', '.join(cluster['queries'])}")
    return result

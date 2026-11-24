"""Evaluate embeddings, ranked retrieval, and grounded generation."""

from __future__ import annotations

import json
import hashlib
import math
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from time import perf_counter
from typing import Any

import httpx

from indexer.pipeline.config import get_settings
from indexer.pipeline.embed import embed

from .lake import atomic_write, write_json
from .tracing import percentile
from .verify import cosine


def json_lines(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def normalize(text: str) -> str:
    return " ".join(re.findall(r"\w+|[%.,]", text.casefold()))


def rank_metrics(rank: int | None) -> dict[str, float]:
    return {
        "recall_at_3": float(rank is not None and rank <= 3),
        "recall_at_5": float(rank is not None and rank <= 5),
        "precision_at_5": 0.2 if rank is not None and rank <= 5 else 0.0,
        "mrr": 1 / rank if rank else 0.0,
        "ndcg_at_5": 1 / math.log2(rank + 1) if rank and rank <= 5 else 0.0,
    }


def grade(question: dict[str, Any], trace: dict[str, Any]) -> dict[str, float]:
    response = trace["response"]
    answered = response["answered_from_context"]
    if question["type"] == "unanswerable":
        return {"abstention_correctness": float(not answered), "correctness": float(not answered)}
    rank = next((
        position for position, row in enumerate(trace["retrieved"], 1)
        if row["doc_id"] == question["gt_doc_id"]
    ), None)
    expected = normalize(question["gt_answer_hint"])
    result = rank_metrics(rank) | {
        "correctness": float(answered and expected in normalize(response["answer"])),
        "false_abstention_rate": float(not answered),
    }
    if answered:
        citations = response["citations"]
        source_rows = [
            row for row in trace["context"]
            if any(all(row[key] == citation[key] for key in ("source", "section", "page"))
                   for citation in citations)
        ]
        quote = re.fullmatch(r'The cited policy states: "(.*)"', response["answer"], flags=re.DOTALL)
        valid = bool(citations) and all(
            any(all(row[key] == citation[key] for key in ("source", "section", "page"))
                for row in source_rows)
            for citation in citations
        )
        supported = bool(quote and any(
            normalize(quote[1]) in normalize(row["text"]) for row in source_rows
        ))
        result.update({
            "citation_validity": float(valid and supported),
            "faithfulness": float(supported), "hallucination_rate": float(not supported),
        })
    return result


def module_metrics(path: Path) -> dict[str, Any]:
    pairs = json.loads(path.read_text(encoding="utf-8"))
    settings = get_settings()
    values: dict[str, list[float]] = {"paraphrase": [], "unrelated": []}
    timings = []
    details = []
    for kind, entries in pairs.items():
        for start_index in range(0, len(entries), 8):
            batch = entries[start_index:start_index + 8]
            start = perf_counter()
            vectors = iter(embed([text for pair in batch for text in pair], settings))
            latency = (perf_counter() - start) * 1000 / (2 * len(batch))
            for left, right in batch:
                score = cosine(next(vectors), next(vectors))
                timings.append(latency)
                values[kind].append(score)
                details.append({
                    "kind": kind, "left": left, "right": right, "cosine": score, "ms_per_text": latency,
                })
    first = embed([pairs["paraphrase"][0][0]], settings)[0]
    second = embed([pairs["paraphrase"][0][0]], settings)[0]
    return {
        "paraphrase_cosine": mean(values["paraphrase"]), "unrelated_cosine": mean(values["unrelated"]),
        "cosine_gap": mean(values["paraphrase"]) - mean(values["unrelated"]),
        "embedding_mean_ms": mean(timings), "embedding_p95_ms": percentile(timings, 0.95),
        "max_absolute_embedding_difference": max(abs(a - b) for a, b in zip(first, second, strict=True)),
        "float32_bytes_per_embedding": len(first) * 4, "pairs": details,
    }


def suite(
    client: httpx.Client, endpoint: str, questions: list[dict[str, Any]], collection: str,
    *, noise: bool = False, retrieval_only: bool = False,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    details = []
    for question in questions:
        text = question["question"]
        if noise:
            text = re.sub(r"\b([A-Za-z])([A-Za-z])([A-Za-z]{4,})", r"\2\1\3", text, count=1)
        response = client.post(
            f"{endpoint.rstrip('/')}/query",
            params={"bypass_cache": "true", "retrieval_only": str(noise or retrieval_only).lower()},
            json={"question": text},
        )
        response.raise_for_status()
        trace = response.json()
        if trace["collection"] != collection:
            raise ValueError(f"evaluation requested {collection} but API used {trace['collection']}")
        scores = grade(question, trace)
        if noise or retrieval_only:
            scores = {key: value for key, value in scores.items() if key in rank_metrics(None)}
        details.append({"golden": question, "trace": trace, "scores": scores})
    keys = sorted({key for row in details for key in row["scores"]})
    metrics = {
        key: mean(row["scores"][key] for row in details if key in row["scores"]) for key in keys
    }
    stages = ("embed", "retrieve", "rerank", "rail", "total")
    if not noise and not retrieval_only:
        stages += ("generate",)
    for stage in stages:
        timings = [row["trace"]["latency_ms"][stage] for row in details]
        metrics[f"p50_{stage}_ms"] = percentile(timings, 0.50)
        metrics[f"p95_{stage}_ms"] = percentile(timings, 0.95)
    return metrics, details


def evaluate(
    endpoint: str, collection: str, golden: Path, pairs: Path, out: Path, label: str, split: str,
    *, retrieval_only: bool = False,
) -> Path:
    questions = [
        row for row in json_lines(golden) if row.get("split", "a") == "a" or split == "ab"
    ]
    if split == "ab":
        questions = [
            row | {"gt_answer_hint": row["after_hint"]} if "after_hint" in row else row
            for row in questions
        ]
    if not questions:
        raise ValueError("no golden questions selected")
    timestamp = datetime.now(timezone.utc)
    prefix = "retrieval_eval" if retrieval_only else "eval"
    base = out / f"{prefix}_{timestamp.strftime('%Y%m%dT%H%M%S%fZ')}_{label}"
    with httpx.Client(timeout=400) as client:
        modules = [module_metrics(pairs) for _ in range(2)]
        first, first_rows = suite(client, endpoint, questions, collection, retrieval_only=retrieval_only)
        second, second_rows = suite(client, endpoint, questions, collection, retrieval_only=retrieval_only)
        noise, noise_rows = suite(client, endpoint, questions, collection, noise=True)
    first_trace = first_rows[0]["trace"]
    golden_hash = hashlib.sha256(json.dumps(
        questions, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")).hexdigest()
    source_commit = os.getenv("GIT_COMMIT")
    if not source_commit:
        source_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    settings = get_settings()
    ordered_keys = sorted(first.keys() & second.keys())
    result = {
        "environment": {
            "timestamp": timestamp.isoformat(), "git_commit": source_commit, "collection": collection,
            "embedding_model": first_trace["embedding_model"], "embedding_version": first_trace["embedding_version"],
            "chunk_size": settings.chunk_size, "chunk_overlap": settings.chunk_overlap,
            "top_k": first_trace["params"]["top_k"], "llm_name": first_trace["model"], "seed": 0,
            "split": split, "golden_sha256": golden_hash, "question_count": len(questions),
            "retrieval_only": retrieval_only,
        },
        "module": modules, "run_1": first, "run_2": second, "noise": noise,
        "mean": {key: mean([first[key], second[key]]) for key in ordered_keys},
        "absolute_difference": {key: abs(first[key] - second[key]) for key in ordered_keys},
        "noise_delta": {key: noise[key] - first[key] for key in sorted(noise.keys() & first.keys())},
    }
    output = base.with_suffix(".json")
    write_json(output, result)
    atomic_write(base.with_name(base.name + "_details.jsonl"), "".join(
        json.dumps(row | {"run": name}, ensure_ascii=False) + "\n"
        for name, rows in (("clean_1", first_rows), ("clean_2", second_rows), ("noise", noise_rows))
        for row in rows
    ).encode("utf-8"))
    lines = ["| Metric | Run 1 | Run 2 | Mean | Absolute difference | Noise delta |",
             "| --- | ---: | ---: | ---: | ---: | ---: |"]
    for key in ordered_keys:
        noise_delta = result["noise_delta"].get(key)
        delta_display = f"{noise_delta:.4f}" if noise_delta is not None else "—"
        lines.append(
            f"| {key} | {first[key]:.4f} | {second[key]:.4f} | {result['mean'][key]:.4f} | "
            f"{result['absolute_difference'][key]:.4f} | {delta_display} |"
        )
    atomic_write(base.with_suffix(".md"), ("\n".join(lines) + "\n").encode("utf-8"))
    return output

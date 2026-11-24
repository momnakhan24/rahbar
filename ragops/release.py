"""Compare measured evaluations and enforce release criteria."""

from __future__ import annotations

import json
import math
from pathlib import Path
from statistics import mean

import yaml

from .lake import atomic_write, write_json


def measured_values(result: dict) -> dict[str, float]:
    modules = result["module"]
    return {
        **{
            f"module/{key}": mean(run[key] for run in modules)
            for key, value in modules[0].items() if isinstance(value, (int, float))
        },
        **result["mean"],
    }


def compare(baseline: Path, candidate: Path, out: Path) -> None:
    """Write the requested before/after or baseline/candidate metric table."""
    original = json.loads(baseline.read_text(encoding="utf-8"))
    proposed = json.loads(candidate.read_text(encoding="utf-8"))
    before = measured_values(original)
    after = measured_values(proposed)
    values = {
        key: {
            "baseline": before[key],
            "candidate": after[key],
            "delta": after[key] - before[key],
        }
        for key in sorted(before.keys() & after.keys())
    }
    def clean_rows(result: Path) -> dict[str, dict]:
        path = result.with_name(result.stem + "_details.jsonl")
        if not path.exists():
            return {}
        rows = (json.loads(line) for line in path.read_text(encoding="utf-8").splitlines())
        return {row["golden"]["id"]: row for row in rows if row["run"] == "clean_1"}

    before_rows = clean_rows(baseline)
    after_rows = clean_rows(candidate)
    common_ids = sorted(before_rows.keys() & after_rows.keys())
    drift = []
    for question_id in common_ids:
        first = before_rows[question_id]["trace"]["retrieved"]
        second = after_rows[question_id]["trace"]["retrieved"]
        if first and second:
            drift.append({
                "id": question_id, "before_similarity": first[0]["score"], "after_similarity": second[0]["score"],
                "before_doc_version": first[0]["doc_version"], "after_doc_version": second[0]["doc_version"],
                "before_doc_id": first[0]["doc_id"], "after_doc_id": second[0]["doc_id"],
            })
    write_json(out.with_suffix(".json"), {
        "baseline_result": str(baseline), "candidate_result": str(candidate), "metrics": values,
        "shared_question_count": len(common_ids), "top1_comparison": drift,
    })
    rows = ["| Metric | Baseline | Candidate | Delta |", "| --- | ---: | ---: | ---: |"]
    for name, labels in values.items():
        rows.append(
            f"| {name} | {labels['baseline']:.6g} | {labels['candidate']:.6g} | {labels['delta']:+.6g} |"
        )
    atomic_write(out.with_suffix(".md"), ("\n".join(rows) + "\n").encode("utf-8"))


def gate(baseline: Path, candidate: Path, config: Path) -> bool:
    prior = json.loads(baseline.read_text(encoding="utf-8"))
    proposed = json.loads(candidate.read_text(encoding="utf-8"))
    if any(
        prior["environment"][key] != proposed["environment"][key]
        for key in ("seed", "split", "llm_name")
    ):
        raise ValueError("release results must use the same split, seed and generator")
    limits = yaml.safe_load(config.read_text(encoding="utf-8"))
    before, after = prior["mean"], proposed["mean"]
    partial = prior["environment"].get("retrieval_only") or proposed["environment"].get("retrieval_only")
    recall = before.get("recall_at_5")
    faithfulness = before.get("faithfulness")
    latency = before.get("p95_total_ms") if not partial else None
    rules = [
        ("recall_at_5", ">=", max(0, recall - limits["recall_at_5_max_drop"]) if recall is not None else None),
        (
            "faithfulness", ">=",
            max(0, faithfulness - limits["faithfulness_max_drop"]) if faithfulness is not None else None,
        ),
        ("p95_total_ms", "<=", latency * limits["p95_latency_baseline_factor"] if latency is not None else None),
        ("abstention_correctness", ">=", before.get("abstention_correctness")),
    ]
    print("| Rule | Candidate | Requirement | Result |")
    print("| --- | ---: | ---: | --- |")
    outcomes = []
    for metric, operator, limit in rules:
        value = after.get(metric) if not partial or metric == "recall_at_5" else None
        valid = (
            value is not None and limit is not None and math.isfinite(value) and math.isfinite(limit)
            and (value >= limit if operator == ">=" else value <= limit)
        )
        display = f"{value:.6g}" if value is not None else "missing"
        requirement = f"{operator} {limit:.6g}" if limit is not None else "unmeasured baseline"
        print(f"| {metric} | {display} | {requirement} | {'PASS' if valid else 'FAIL'} |")
        outcomes.append(valid)
    print("RELEASE" if all(outcomes) else "REJECT")
    return all(outcomes)

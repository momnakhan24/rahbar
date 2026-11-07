#!/usr/bin/env python3
"""Score a running RAHBAR against a golden set, and gate CI on the result (section 5).

    python eval/run_eval.py --api http://<ingress>                 # your corpus
    python eval/run_eval.py --api ... --golden eval/fixtures/golden.fixture.yaml
    python eval/run_eval.py --api ... --update-baseline            # after a deliberate improvement

Exit code 0 when every gate passes, 1 when any fails. CI relies on that exit code.

The runner talks to the API, reads the golden set, writes results.json, and returns a
non-zero exit code when a quality gate fails.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

import httpx
import yaml

HERE = Path(__file__).resolve().parent

# The gate from section 5.4. Change these only with a reason written in docs/PIPELINE.md.
MAX_RECALL5_DROP = 0.05        # recall@5 may fall at most 5 points below the baseline
MIN_CITATION_VALIDITY = 0.95   # at least 95% of citations must match retrieved passages
REQUIRED_ABSTENTION = 1.0      # every must-abstain question must be declined


def load_golden(path: Path) -> list[dict]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    questions = data.get("questions") or []
    if not questions:
        sys.exit(f"no questions in {path}")
    return questions


def ask(client: httpx.Client, api: str, question: str) -> dict:
    """POST one question and return the AskResponse as a dict (see api/app/schemas.py)."""
    response = client.post(f"{api.rstrip('/')}/api/ask", json={"question": question})
    response.raise_for_status()
    return response.json()


def recall_at_k(relevant: list[dict], retrieved: list[dict], k: int) -> float | None:
    """Fraction of the relevant (source, section) pairs found in the top k retrieved.
    Return None when the question has no relevant passages (must-abstain questions)."""
    if not relevant:
        return None

    def normal(value: object) -> str:
        return re.sub(r"[^a-z0-9]+", " ", str(value).lower()).strip()

    def matches(gold: dict, item: dict) -> bool:
        if normal(gold.get("source", "")) != normal(item.get("source", "")):
            return False
        expected = normal(gold.get("section", ""))
        actual = normal(item.get("section", ""))
        return bool(expected) and (actual == expected or actual.startswith(expected + " "))

    top = retrieved[:k]
    found = sum(1 for target in relevant if any(matches(target, item) for item in top))
    return found / len(relevant)


def citation_validity(response: dict) -> float | None:
    """Fraction of the response's citations that match a passage in response['retrieved'].
    Return None when there are no citations."""
    retrieved = response.get("retrieved") or []
    citations = response.get("citations") or []
    if not citations:
        return None
    refs = {
        (item.get("source"), item.get("section"), item.get("page"))
        for item in retrieved
    }
    valid = sum(
        (item.get("source"), item.get("section"), item.get("page")) in refs
        for item in citations
    )
    return valid / len(citations)


def summarise(rows: list[dict]) -> dict:
    """Overall recall@3, recall@5, citation validity and abstention correctness, plus
    recall@5 broken down by question type. This dict becomes results.json."""
    recalls: dict[int, list[float]] = {3: [], 5: []}
    by_type: dict[str, list[float]] = {}
    citation_valid = 0
    citation_total = 0
    expected_term_correct = 0
    expected_term_total = 0
    abstain_correct = 0
    abstain_total = 0
    details = []
    for row in rows:
        response = row.get("response") or {}
        retrieved = response.get("retrieved") or []
        relevant = row.get("relevant") or []
        r3 = recall_at_k(relevant, retrieved, 3)
        r5 = recall_at_k(relevant, retrieved, 5)
        for k, value in ((3, r3), (5, r5)):
            if value is not None:
                recalls[k].append(value)
        if r5 is not None:
            by_type.setdefault(str(row.get("type", "ordinary")), []).append(r5)
        citations = response.get("citations") or []
        validity = citation_validity(response)
        if validity is not None:
            citation_valid += round(validity * len(citations))
            citation_total += len(citations)
        if row.get("must_abstain"):
            abstain_total += 1
            abstain_correct += not bool(response.get("answered_from_context", False))
        expected = row.get("expect")
        expected_match = None
        if expected:
            expected_term_total += 1
            expected_match = str(expected).casefold() in str(response.get("answer", "")).casefold()
            expected_term_correct += expected_match
        details.append({
            "id": row.get("id"),
            "type": row.get("type", "ordinary"),
            "recall_at_3": r3,
            "recall_at_5": r5,
            "citation_validity": validity,
            "expected_term_match": expected_match,
            "abstention_correct": (
                not bool(response.get("answered_from_context", False))
                if row.get("must_abstain") else None
            ),
        })
    def average(values: list[float]) -> float | None:
        return sum(values) / len(values) if values else None

    return {
        "recall_at_3": average(recalls[3]),
        "recall_at_5": average(recalls[5]),
        "recall_at_5_by_type": {key: average(values) for key, values in sorted(by_type.items())},
        "citation_validity": citation_valid / citation_total if citation_total else None,
        "abstention_correctness": abstain_correct / abstain_total if abstain_total else None,
        "must_abstain_correct": abstain_correct,
        "must_abstain_total": abstain_total,
        "citation_valid": citation_valid,
        "citation_total": citation_total,
        "expected_term_accuracy": (
            expected_term_correct / expected_term_total if expected_term_total else None
        ),
        "expected_term_correct": expected_term_correct,
        "expected_term_total": expected_term_total,
        "per_question": details,
    }


def gate(results: dict, baseline: dict | None) -> list[str]:
    """Return one message per failed gate (section 5.4); an empty list means pass."""
    failures = []
    recall = results.get("recall_at_5")
    if baseline is None:
        failures.append("no committed baseline is available")
    elif recall is None or baseline.get("recall_at_5") is None:
        failures.append("recall@5 is missing from the result or baseline")
    elif recall < float(baseline["recall_at_5"]) - MAX_RECALL5_DROP:
        failures.append(
            f"recall@5 {recall:.3f} is more than {MAX_RECALL5_DROP:.0%} below "
            f"baseline {float(baseline['recall_at_5']):.3f}"
        )
    if results.get("must_abstain_total", 0) and results.get("must_abstain_correct", 0) \
            != results.get("must_abstain_total"):
        failures.append("one or more must-abstain questions were answered from context")
    citation_validity = results.get("citation_validity")
    if citation_validity is None or citation_validity < MIN_CITATION_VALIDITY:
        failures.append(
            f"citation validity {citation_validity} is below {MIN_CITATION_VALIDITY:.0%}"
        )
    abstention = results.get("abstention_correctness")
    if abstention is not None and abstention < REQUIRED_ABSTENTION:
        failures.append("must-abstain correctness is below 100%")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate RAHBAR against a golden set.")
    parser.add_argument("--api", required=True, help="base URL, e.g. http://192.168.49.2")
    parser.add_argument("--host", help="Host header, when your Ingress rule names a host")
    parser.add_argument("--timeout", type=float, default=120.0,
                        help="per-request timeout; increase for CPU-only local generation")
    parser.add_argument("--golden", type=Path, default=HERE / "golden.yaml")
    parser.add_argument("--baseline", type=Path, default=HERE / "baseline.json")
    parser.add_argument("--out", type=Path, default=HERE / "results.json")
    parser.add_argument("--responses-out", type=Path,
                        help="optional raw responses for per-answer grounding review")
    parser.add_argument("--update-baseline", action="store_true",
                        help="write these results as the new baseline")
    args = parser.parse_args()

    questions = load_golden(args.golden)
    rows = []
    headers = {"Host": args.host} if args.host else {}
    with httpx.Client(timeout=args.timeout, headers=headers) as client:
        for q in questions:
            started = time.perf_counter()
            response = ask(client, args.api, q["question"])
            rows.append({
                "id": q["id"], "type": q.get("type", "ordinary"),
                "must_abstain": bool(q.get("must_abstain", False)),
                "relevant": q.get("relevant") or [],
                "expect": q.get("expect"),
                "response": response,
                "seconds": round(time.perf_counter() - started, 2),
            })
            if args.responses_out:
                args.responses_out.write_text(json.dumps(rows, indent=2), encoding="utf-8")
            print(f"  {q['id']:<5} {rows[-1]['seconds']:>6.2f}s  {q['question'][:60]}")

    try:
        results = summarise(rows)
        baseline = json.loads(args.baseline.read_text()) if args.baseline.exists() else None
        failures = gate(results, baseline)
    except NotImplementedError as exc:
        print(f"\nnot implemented yet: {exc}")
        return 2

    results["golden"] = str(args.golden)
    results["questions"] = len(rows)
    args.out.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nresults written to {args.out}")
    if args.update_baseline:
        args.baseline.write_text(json.dumps(results, indent=2), encoding="utf-8")
        print(f"baseline updated: {args.baseline}")

    if failures:
        print("\nGATE FAILED")
        for message in failures:
            print(f"  - {message}")
        return 1
    print("\ngate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())

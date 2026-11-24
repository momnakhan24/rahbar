"""Load staged source manifests and write runnable verification evidence."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from typing import Any

from indexer.pipeline.extract import extract

from .lake import Lake, atomic_write, write_json
from .verify import Embed, Source


def load_source(root: Path, entry: dict[str, Any], lake: Lake) -> tuple[Source, bytes, str]:
    path = root / entry["file"]
    if path.resolve().parent != root.resolve():
        raise ValueError(f"source file must be directly inside {root}")
    raw = path.read_bytes()
    error = None
    pages: tuple[str, ...] = ()
    version = str(entry.get("version", ""))
    raw_hash = hashlib.sha256(raw).hexdigest()
    prior = lake.manifest["versions"].get(entry.get("doc_id"), {}).get(version)
    if prior and prior["raw_hash"] == raw_hash:
        pages = tuple(prior["document"]["pages"])
    else:
        try:
            document = extract(str(path), version, False)
            pages = tuple(page.text for page in document.pages)
        except Exception as failure:
            error = f"{type(failure).__name__}: {failure}"
    truncated = path.suffix.lower() == ".pdf" and b"%%EOF" not in raw[-1024:]
    checksum = entry.get("sha256")
    if checksum and raw_hash != checksum:
        error = "raw bytes differ from the source manifest checksum"
    return (
        Source(
            doc_id=entry.get("doc_id", ""), source=entry.get("source", ""),
            title=entry.get("title", ""), version=version, page_count=entry.get("page_count"),
            access=entry.get("access", ""), pages=pages, extraction_error=error, truncated=truncated,
        ),
        raw,
        path.suffix.lower(),
    )


def ingest(
    lake: Lake, inbox: Path, output: Path, run_id: str, embed: Embed, *,
    near_threshold: float, min_length: int, snapshot: bool,
) -> dict[str, Any]:
    entries = json.loads((inbox / "manifest.json").read_text(encoding="utf-8"))
    counts = Counter(dict.fromkeys(("seen", "unchanged", "new", "changed", "quarantined", "deleted"), 0))
    reports = []
    present = set()
    for entry in entries:
        if snapshot and not (inbox / entry["file"]).is_file():
            continue
        document, raw, suffix = load_source(inbox, entry, lake)
        result, action = lake.admit(document, raw, suffix, run_id, embed, near_threshold, min_length)
        present.add(document.doc_id)
        counts["seen"] += 1
        counts[action] += 1
        reports.append({
            "file": entry["file"], "doc_id": document.doc_id, "version": document.version,
            "outcome": action, "checks": [asdict(check) for check in result.checks],
            "suspicious_content": result.suspicious_content,
        })
    if snapshot:
        for doc_id in sorted(set(lake.manifest["active"]) - present):
            lake.delete(doc_id)
            counts["deleted"] += 1
    report = {
        "run_id": run_id, "near_duplicate_threshold": near_threshold, "min_length": min_length,
        "snapshot": snapshot, "counts": dict(counts), "documents": reports,
    }
    path = output / f"verification_report_{run_id}"
    write_json(path.with_suffix(".json"), report)
    summary = [
        "| File | Outcome | Quality | Completeness | Recency | Uniqueness | Suspicious |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in reports:
        states = ["pass" if check["passed"] else "fail" for check in row["checks"]]
        summary.append("| " + " | ".join([
            row["file"], row["outcome"], *states, str(row["suspicious_content"]),
        ]) + " |")
    atomic_write(path.with_suffix(".md"), ("\n".join(summary) + "\n").encode())
    return report

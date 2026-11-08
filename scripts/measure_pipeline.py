"""Run reproducible extraction/chunk experiments inside the indexer image.

Mount the repository at /workspace; set PYTHONPATH=/app. Extracted public text
and vectors are cached in ignored work/, while measured summaries go to evidence.
This measures retrieval only; run eval/run_eval.py separately for generation.
"""
from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import sys
from dataclasses import asdict
from pathlib import Path

import numpy as np
import httpx

from pipeline.chunk import chunk
from pipeline.clean import clean
from pipeline.config import get_settings
from measurement_vectors import embed
from pipeline.extract import extract
from pipeline.models import Document, Page
from pipeline.run import discover


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("/workspace"))
    parser.add_argument("--extract-only", action="store_true")
    args = parser.parse_args()
    root = args.root
    cache = root / "work" / "measurements"
    cache.mkdir(parents=True, exist_ok=True)
    evidence = root / "docs" / "evidence"
    evidence.mkdir(parents=True, exist_ok=True)
    documents = []
    extraction = []
    extractor_hash = hashlib.sha256(Path(inspect.getfile(extract)).read_bytes()).hexdigest()
    for path, version, superseded in discover(str(root / "corpus" / "raw")):
        saved = cache / f"{path.name}.json"
        source_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        data = json.loads(saved.read_text()) if saved.exists() else {}
        if (data.get("source_sha256") == source_hash
                and data.get("extractor_sha256") == extractor_hash):
            doc = Document(data["source"], data["doc_version"], data["superseded"],
                           [Page(**page) for page in data["pages"]])
        else:
            doc = extract(str(path), version, superseded)
            data = {**asdict(doc), "source_sha256": source_hash,
                    "extractor_sha256": extractor_hash}
            saved.write_text(json.dumps(data), encoding="utf-8")
        extraction.append({"source": doc.source, "pages": len(doc.pages),
                           "ocr_pages": [p.page for p in doc.pages if p.ocr],
                           "words": sum(len(p.text.split()) for p in doc.pages),
                           "verified_pdf_cache_reuse": bool(data.get("reused_pdf_extractor_from"))})
        documents.append(clean(doc))
        print(json.dumps(extraction[-1]), flush=True)
    (evidence / "extraction.json").write_text(json.dumps(extraction, indent=2))
    if args.extract_only:
        return
    sys.path.insert(0, str(root / "eval"))
    from run_eval import load_golden, recall_at_k

    settings = get_settings()
    model_response = httpx.get(f"{settings.ollama_url}/api/tags", timeout=15)
    model_response.raise_for_status()
    model_digest = next(m["digest"] for m in model_response.json()["models"]
                        if m["name"].split(":")[0] == settings.embed_model.split(":")[0])
    fingerprint = hashlib.sha256(json.dumps({
        "extractor": extractor_hash,
        "chunker": hashlib.sha256(Path(inspect.getfile(chunk)).read_bytes()).hexdigest(),
        "sources": [(p.name, hashlib.sha256(p.read_bytes()).hexdigest())
                    for p, _, _ in discover(str(root / "corpus" / "raw"))],
        "golden": hashlib.sha256((root / "eval" / "golden.yaml").read_bytes()).hexdigest(),
        "model": model_digest,
    }, sort_keys=True).encode()).hexdigest()
    golden = load_golden(root / "eval" / "golden.yaml")
    query_vectors = np.array(embed([q["question"] for q in golden], settings))
    query_vectors /= np.linalg.norm(query_vectors, axis=1, keepdims=True)
    original = sum(len(p.text.split()) for d in documents for p in d.pages)
    results = []
    for size, overlap in ((250, 30), (400, 50), (600, 75)):
        previous = evidence / "chunk-sweep.json"
        prior = json.loads(previous.read_text()) if previous.exists() else []
        completed = next((r for r in prior if r['size'] == size and r['overlap'] == overlap
                          and r.get('fingerprint') == fingerprint), None)
        if completed:
            results.append(completed)
            continue
        chunks = [c for d in documents for c in chunk(d, size, overlap)]
        vectors = np.array(embed([c.text for c in chunks], settings))
        vectors /= np.linalg.norm(vectors, axis=1, keepdims=True)
        scores = query_vectors @ vectors.T
        recalls = {3: [], 5: []}
        by_type: dict[str, list[float]] = {}
        for index, question in enumerate(golden):
            current = [i for i, c in enumerate(chunks) if not c.superseded]
            best = sorted(current, key=lambda i: scores[index, i], reverse=True)[:5]
            retrieved = [chunks[i].metadata() for i in best]
            for k in (3, 5):
                value = recall_at_k(question.get("relevant", []), retrieved, k)
                if value is not None:
                    recalls[k].append(value)
                    if k == 5:
                        by_type.setdefault(question.get("type", "ordinary"), []).append(value)
        row = {"size": size, "overlap": overlap, "chunks": len(chunks),
               "fingerprint": fingerprint, "model_digest": model_digest,
               "dimension": vectors.shape[1], "embed_model": settings.embed_model,
               "storage_amplification": sum(len(c.text.split()) for c in chunks) / original,
               "recall_at_3": float(np.mean(recalls[3])),
               "recall_at_5": float(np.mean(recalls[5])),
               "recall_at_5_by_type": {k: float(np.mean(v)) for k, v in by_type.items()},
               "method": "exact cosine over current-version chunks; retrieval only"}
        results.append(row)
        print(json.dumps(row), flush=True)
        (evidence / "chunk-sweep.json").write_text(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()

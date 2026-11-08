"""Measure semantic-cache thresholds using labels fixed before the experiment."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import yaml

from pipeline.config import get_settings
from pipeline.embed import embed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("/workspace"))
    args = parser.parse_args()
    pairs = yaml.safe_load((args.root / "eval/cache-pairs.yaml").read_text())["pairs"]
    settings = get_settings()
    vectors = np.array(embed([p[k] for p in pairs for k in ("query", "candidate")], settings))
    vectors /= np.linalg.norm(vectors, axis=1, keepdims=True)
    for i, pair in enumerate(pairs):
        pair["similarity"] = float(vectors[2 * i] @ vectors[2 * i + 1])
    sweep = []
    for threshold in (0.85, 0.90, 0.94, 0.96, 0.98):
        sweep.append({
            "threshold": threshold,
            "true_hits": sum(p["similarity"] >= threshold and p["same_answer"] for p in pairs),
            "false_hits": sum(p["similarity"] >= threshold and not p["same_answer"]
                              for p in pairs),
            "misses": sum(p["similarity"] < threshold and p["same_answer"] for p in pairs),
        })
    result = {"captured_at": datetime.now(timezone.utc).isoformat(),
              "embed_model": settings.embed_model, "pairs": pairs, "thresholds": sweep,
              "scope": "offline cosine decision study; Redis latency measured separately"}
    target = args.root / "docs/evidence/cache-sweep.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

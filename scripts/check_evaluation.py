"""Check that committed real-corpus scores are reproducible from reviewed responses."""
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from eval.run_eval import gate, load_golden, summarise  # noqa: E402


def main() -> int:
    golden = load_golden(ROOT / 'eval/golden.yaml')
    rows = json.loads((ROOT / 'docs/evidence/final-responses.json').read_text(encoding='utf-8'))
    results = json.loads((ROOT / 'eval/results.json').read_text(encoding='utf-8'))
    baseline = json.loads((ROOT / 'eval/baseline.json').read_text(encoding='utf-8'))
    if len(golden) < 15 or len(rows) != len(golden):
        raise ValueError('real response count does not match the assignment golden set')
    if results.get('questions') != len(golden) or baseline.get('questions') != len(golden):
        raise ValueError('result/baseline question count does not match the real golden set')
    for question, row in zip(golden, rows):
        for key in ('id', 'question', 'relevant'):
            if row.get(key) != question.get(key):
                raise ValueError(f'response provenance mismatch: {question["id"]} {key}')
    for key, measured in summarise(rows).items():
        if results.get(key) != measured:
            raise ValueError(f'committed results disagree with recorded responses: {key}')
    failures = gate(results, baseline)
    if failures:
        raise ValueError('; '.join(failures))
    print(f'Committed real evaluation verified: {len(rows)} questions; regression gate passed')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

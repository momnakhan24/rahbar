"""Deliberate stage B fault: fixed 100-word windows, zero overlap.

Run in the indexer image with the repository mounted at /workspace and
PYTHONPATH=/app. Reuses source-verified extraction from measure_pipeline.py.
"""
from __future__ import annotations

import hashlib
import inspect
import json
import sys
from pathlib import Path

import numpy as np

from pipeline.chunk import chunk
from pipeline.clean import clean
from pipeline.config import get_settings
from pipeline.embed import embed
from pipeline.extract import extract
from pipeline.models import Chunk, Document, Page
from pipeline.run import discover


def main() -> None:
    root = Path('/workspace')
    sys.path.insert(0, str(root / 'eval'))
    from run_eval import load_golden, recall_at_k

    pieces = []
    extractor_hash = hashlib.sha256(Path(inspect.getfile(extract)).read_bytes()).hexdigest()
    for path, version, superseded in discover(str(root / 'corpus/raw')):
        data = json.loads((root / 'work/measurements' / f'{path.name}.json').read_text())
        assert data['source_sha256'] == hashlib.sha256(path.read_bytes()).hexdigest()
        assert data['extractor_sha256'] == extractor_hash
        doc = clean(Document(data['source'], version, superseded,
                             [Page(**p) for p in data['pages']]))
        # Keep provenance using the normal section parser, but deliberately ignore
        # its boundaries when forming fixed windows. Label by the first word's
        # source section, so the failure does not manufacture missing metadata.
        structured = chunk(doc, 100000, 0)
        for page in doc.pages:
            words = []
            for part in [c for c in structured if c.page == page.page]:
                words.extend((word, part.section) for word in part.text.split())
            for start in range(0, len(words), 100):
                window = words[start:start + 100]
                if window:
                    pieces.append(Chunk(f'fixed-{len(pieces)}',
                                        ' '.join(w for w, _ in window), doc.source,
                                        window[0][1], page.page, version, superseded))
    settings = get_settings()
    questions = load_golden(root / 'eval/golden.yaml')
    queries = np.array(embed([q['question'] for q in questions], settings))
    vectors = np.array(embed([p.text for p in pieces], settings))
    queries /= np.linalg.norm(queries, axis=1, keepdims=True)
    vectors /= np.linalg.norm(vectors, axis=1, keepdims=True)
    scores = queries @ vectors.T
    rows = []
    for index, question in enumerate(questions):
        current = [i for i, p in enumerate(pieces) if not p.superseded]
        best = sorted(current, key=lambda i: scores[index, i], reverse=True)[:5]
        retrieved = [pieces[i].metadata() for i in best]
        rows.append({'id': question['id'], 'type': question['type'],
                     'recall_at_3': recall_at_k(question.get('relevant', []), retrieved, 3),
                     'recall_at_5': recall_at_k(question.get('relevant', []), retrieved, 5),
                     'retrieved': retrieved})
    result = {'fault': 'B: fixed 100-word chunks, no overlap; whitespace token approximation',
              'method': 'exact cosine, same corpus/model/golden; retrieval only',
              'chunks': len(pieces), 'dimension': vectors.shape[1],
              'recall_at_3': float(np.mean([r['recall_at_3'] for r in rows if r['recall_at_3'] is not None])),
              'recall_at_5': float(np.mean([r['recall_at_5'] for r in rows if r['recall_at_5'] is not None])),
              'questions': rows}
    target = root / 'docs/evidence/failure-b-fixed-chunks.json'
    target.write_text(json.dumps(result, indent=2))
    print(json.dumps({k: v for k, v in result.items() if k != 'questions'}), flush=True)


if __name__ == '__main__':
    main()

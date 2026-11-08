"""Resumable embeddings for experiments, separate from production indexing."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import httpx


def embed(texts, settings):
    path = Path('/workspace/work/measurements/vectors.jsonl')
    with httpx.Client(timeout=180) as client:
        tags = client.get(f'{settings.ollama_url}/api/tags')
        tags.raise_for_status()
        model = next(m for m in tags.json()['models']
                     if m['name'].split(':')[0] == settings.embed_model.split(':')[0])
        pin = model['digest']
        keys = [hashlib.sha256((pin + '\n' + t).encode()).hexdigest() for t in texts]
        saved = {}
        if path.exists():
            for line in path.read_text().splitlines():
                try:
                    entry = json.loads(line)
                    saved[entry['key']] = entry['vector']
                except (ValueError, KeyError):
                    continue  # ignore only an incomplete append after interruption
        missing = list(dict.fromkeys(k for k in keys if k not in saved))
        text_by_key = dict(zip(keys, texts))
        with path.open('a') as output:
            for start in range(0, len(missing), 16):
                batch = missing[start:start + 16]
                response = client.post(f'{settings.ollama_url}/api/embed', json={
                    'model': settings.embed_model, 'input': [text_by_key[k] for k in batch],
                    'options': {'num_thread': 4},
                })
                response.raise_for_status()
                vectors = response.json()['embeddings']
                if len(vectors) != len(batch):
                    raise ValueError('unexpected embedding vector count')
                for key, vector in zip(batch, vectors):
                    saved[key] = vector
                    output.write(json.dumps({'key': key, 'vector': vector}) + '\n')
                output.flush()
                print(f'cached embeddings {min(start + 16, len(missing))}/{len(missing)}', flush=True)
    return [saved[k] for k in keys]

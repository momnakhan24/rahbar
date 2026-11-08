"""Stage 2: Clean. Remove artefacts without destroying structure."""

from __future__ import annotations

import re
from collections import Counter

from .models import Document


def _normal(value: str) -> str:
    return " ".join(value.lower().split())


def clean(doc: Document) -> Document:
    """Strip headers and footers that repeat on every page; keep headings and
    section boundaries, because chunking and citations depend on them."""
    if not doc.pages:
        return doc
    candidates: Counter[str] = Counter()
    for page in doc.pages:
        lines = [line.strip() for line in page.text.splitlines() if line.strip()]
        for line in set(lines[:2] + lines[-2:]):
            candidates[_normal(line)] += 1
    minimum = max(2, (len(doc.pages) + 1) // 2)
    repeated = {line for line, count in candidates.items() if count >= minimum}
    for page in doc.pages:
        kept = []
        for line in page.text.splitlines():
            value = line.strip()
            if not value:
                continue
            if _normal(value) in repeated:
                continue
            if re.fullmatch(r"(?:page\s*)?\d+(?:\s*(?:of|/)\s*\d+)?", value, re.I):
                continue
            kept.append(value)
        page.text = "\n".join(kept)
    return doc

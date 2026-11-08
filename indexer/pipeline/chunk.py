"""Stage 3: Chunk. Structure-aware, with overlap."""

from __future__ import annotations

import hashlib
import re

from .models import Chunk, Document

_HEADING = re.compile(
    r"^\s*(?:#{1,6}\s+|\d+(?:\.\d+)*\s+|[A-Z][A-Z\s:&()/-]{5,}$)"
)
_SENTENCE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9(])")
_NUMBERED = re.compile(r"^\d+(?:\.\d+)*\.?(?:\s+|$)")


def _count(text: str) -> int:
    """Whitespace-delimited words are the pipeline's documented token approximation."""
    return len(text.split())


def _tail(text: str, count: int) -> str:
    return " ".join(text.split()[-count:]) if count else ""


def _split_long(text: str, size: int, overlap: int) -> list[str]:
    words = text.split()
    step = max(1, size - overlap)
    return [" ".join(words[i:i + size]) for i in range(0, len(words), step)]


def chunk(doc: Document, size: int, overlap: int) -> list[Chunk]:
    """Split on sections, then paragraphs, then sentences, keeping each chunk under
    `size` tokens, with `overlap` tokens shared between neighbours. Every chunk keeps
    the section heading it sits under, its page, doc_version and superseded."""
    if size < 1 or overlap < 0 or overlap >= size:
        raise ValueError("chunk size must be positive and overlap must be smaller than size")
    output: list[Chunk] = []
    position = 0

    def emit(value: str, heading: str, page_number: int) -> None:
        nonlocal position
        value = value.strip()
        if not value:
            return
        position += 1
        stable = f"{doc.source}|{doc.doc_version}|{page_number}|{position}|{value}"
        chunk_id = hashlib.sha256(stable.encode("utf-8")).hexdigest()[:20]
        output.append(Chunk(
            id=chunk_id, text=value, source=doc.source, section=heading,
            page=page_number, doc_version=doc.doc_version, superseded=doc.superseded,
        ))

    for page in doc.pages:
        section = "Document"
        markdown_section = False
        groups: list[tuple[str, list[str]]] = []
        for paragraph in re.split(r"\n\s*\n", page.text):
            lines = [line.strip() for line in paragraph.splitlines() if line.strip()]
            body: list[str] = []
            for line in lines:
                numbered = bool(_NUMBERED.match(line))
                markdown = line.startswith("#")
                heading = markdown or (bool(_HEADING.match(line)) and not numbered)
                clause = numbered and not markdown_section
                if heading or clause:
                    if body:
                        text = " ".join(body)
                        groups.append((section, [part.strip() for part in _SENTENCE.split(text) if part.strip()]))
                        body = []
                    section = line.lstrip("# ").strip()
                    markdown_section = markdown
                    # A PDF clause contains both its identifier and policy text.
                    # Keep that text in evidence instead of discarding the line.
                    if clause:
                        body.append(line)
                else:
                    body.append(line)
            if body:
                text = " ".join(body)
                groups.append((section, [part.strip() for part in _SENTENCE.split(text) if part.strip()]))

        for heading, sentences in groups:
            buffer = ""
            for sentence in sentences:
                if _count(sentence) > size:
                    if buffer:
                        emit(buffer, heading, page.page)
                        buffer = ""
                    windows = _split_long(sentence, size, overlap)
                    for window in windows[:-1]:
                        emit(window, heading, page.page)
                    buffer = windows[-1] if windows else ""
                    continue
                candidate = f"{buffer} {sentence}".strip()
                if _count(candidate) <= size:
                    buffer = candidate
                    continue
                emit(buffer, heading, page.page)
                buffer = f"{_tail(buffer, overlap)} {sentence}".strip()
                if _count(buffer) > size:
                    words = buffer.split()
                    emit(" ".join(words[:size]), heading, page.page)
                    buffer = f"{_tail(' '.join(words[:size]), overlap)} {' '.join(words[size:])}".strip()
            emit(buffer, heading, page.page)
    return output

"""Check extracted source documents before admitting them to the lake."""

from __future__ import annotations

import hashlib
import math
import re
import unicodedata
from dataclasses import dataclass
from typing import Callable, Sequence

INSTRUCTION = re.compile(
    r"\b(?:ignore|disregard|override)\b.{0,60}\b(?:instructions|rules|prompt)\b"
    r"|\b(?:reveal|print|expose)\b.{0,40}\bsystem prompt\b",
    re.IGNORECASE | re.DOTALL,
)
Embed = Callable[[list[str]], list[list[float]]]


def content_hash(text: str) -> str:
    normalized = " ".join(unicodedata.normalize("NFKC", text).casefold().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def cosine(a: Sequence[float], b: Sequence[float]) -> float:
    dot = math.fsum(x * y for x, y in zip(a, b, strict=True))
    magnitude = math.hypot(*a) * math.hypot(*b)
    return dot / magnitude if magnitude else 0.0


def version_key(version: str) -> tuple[int, ...]:
    if not re.fullmatch(r"\d+(?:[.-]\d+)*", version):
        raise ValueError("expected a numeric version or date")
    return tuple(int(part) for part in re.split(r"[.-]", version))


@dataclass(frozen=True)
class Source:
    doc_id: str
    source: str
    title: str
    version: str
    page_count: int | None
    access: str
    pages: tuple[str, ...]
    extraction_error: str | None = None
    truncated: bool = False

    @property
    def text(self) -> str:
        return "\n\n".join(self.pages)


@dataclass(frozen=True)
class Fingerprint:
    doc_id: str
    version: str
    digest: str
    vector: list[float]


@dataclass(frozen=True)
class Check:
    name: str
    passed: bool
    reason: str


@dataclass(frozen=True)
class Verification:
    checks: tuple[Check, ...]
    suspicious_content: bool
    fingerprint: Fingerprint | None

    @property
    def accepted(self) -> bool:
        return all(check.passed for check in self.checks)


def verify(
    item: Source,
    active: Sequence[Fingerprint],
    embed: Embed,
    near_threshold: float,
    min_length: int,
) -> Verification:
    text = item.text
    bad_characters = sum(
        character == "\ufffd" or (not character.isprintable() and not character.isspace())
        for character in text
    )
    quality = item.extraction_error
    if not quality and len(text.strip()) < min_length:
        quality = "extracted text below minimum length"
    if not quality and bad_characters / max(1, len(text)) > 0.01:
        quality = "too many replacement or non-printable characters"

    missing = [
        field for field in ("doc_id", "source", "title", "version", "page_count", "access")
        if not getattr(item, field)
    ]
    incomplete = None
    if missing:
        incomplete = "missing " + ", ".join(missing)
    elif item.truncated or item.page_count != len(item.pages):
        incomplete = "truncation marker or page count mismatch"

    digest = content_hash(text)
    current = next((entry for entry in active if entry.doc_id == item.doc_id), None)
    recency = None
    try:
        incoming_version = version_key(item.version)
        if current and incoming_version < version_key(current.version):
            recency = f"older than active version {current.version}"
        elif current and incoming_version == version_key(current.version) and digest != current.digest:
            recency = "changed content must declare a newer version"
    except ValueError as error:
        recency = str(error)

    peers = sorted(
        (entry for entry in active if entry.doc_id != item.doc_id), key=lambda entry: entry.doc_id
    )
    exact = next((entry for entry in peers if entry.digest == digest), None)
    duplicate = f"exact duplicate of {exact.doc_id}" if exact else None
    vector = []
    uniqueness_checked = exact is not None
    if not quality and not duplicate:
        vector = current.vector if current and current.digest == digest else embed([text])[0]
        uniqueness_checked = True
        nearest = max(((cosine(vector, peer.vector), peer.doc_id) for peer in peers), default=None)
        if nearest and nearest[0] >= near_threshold:
            duplicate = f"near duplicate of {nearest[1]} (cosine {nearest[0]:.6f})"
    if not uniqueness_checked:
        duplicate = "semantic check skipped because another verification check failed"

    checks = (
        Check("quality", quality is None, quality or "extracted text passed quality checks"),
        Check("completeness", incomplete is None, incomplete or "metadata and page count confirmed"),
        Check("recency", recency is None, recency or "version is current or newer"),
        Check("uniqueness", duplicate is None, duplicate or "no exact or semantic duplicate"),
    )
    fingerprint = Fingerprint(item.doc_id, item.version, digest, vector) if vector and not duplicate else None
    return Verification(checks, bool(INSTRUCTION.search(text)), fingerprint)

"""Persist source bytes and extracted pages before publishing retrieval updates."""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from collections.abc import Iterator
from contextlib import closing, contextmanager
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any
from uuid import uuid4

from .verify import Embed, Fingerprint, Source, Verification, verify


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(dir=path.parent, delete=False) as handle:
        temporary = Path(handle.name)
    try:
        temporary.write_bytes(data)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def write_json(path: Path, payload: Any) -> None:
    atomic_write(path, (json.dumps(payload, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))


def safe_id(value: str) -> str:
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]*", value):
        raise ValueError(f"unsafe document identifier: {value!r}")
    return value


@contextmanager
def lake_writer(root: Path) -> Iterator[None]:
    """Serialize writes from manual Jobs and the scheduled ingestion workload."""
    directory = root / "lake"
    directory.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(directory / ".writer.sqlite3", timeout=30)) as lock:
        lock.execute("BEGIN IMMEDIATE")
        try:
            yield
        finally:
            lock.rollback()


class Lake:
    """One writer owns the manifest. Immutable revision bytes survive interrupted runs."""

    def __init__(self, root: Path, *, preview: bool = False) -> None:
        self.root = root
        self.preview = preview
        self.manifest_path = root / "lake" / "manifest.json"
        self.manifest: dict[str, Any] = (
            json.loads(self.manifest_path.read_text(encoding="utf-8"))
            if self.manifest_path.exists()
            else {"revision": 0, "active": {}, "versions": {}, "changelog": []}
        )

    def fingerprints(self) -> list[Fingerprint]:
        return [
            Fingerprint(**self.manifest["versions"][doc_id][version]["fingerprint"])
            for doc_id, version in sorted(self.manifest["active"].items())
        ]

    def _record(self, action: str, doc_id: str, version: str) -> None:
        self.manifest["revision"] += 1
        self.manifest["changelog"].append({
            "revision": self.manifest["revision"],
            "action": action,
            "doc_id": doc_id,
            "version": version,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        if not self.preview:
            write_json(self.manifest_path, self.manifest)

    def materialize_current(self) -> None:
        """Project active bytes from the authoritative revision manifest."""
        directory = self.root / "lake" / "current"
        expected = set()
        for doc_id, version in self.manifest["active"].items():
            archive = self.root / self.manifest["versions"][doc_id][version]["raw_path"]
            destination = directory / doc_id / version / archive.name
            expected.add(destination)
            if not destination.is_file():
                atomic_write(destination, archive.read_bytes())
        for existing in directory.glob("*/*/source.*"):
            if existing not in expected:
                existing.unlink()

    def admit(
        self,
        document: Source,
        raw: bytes,
        suffix: str,
        run_id: str,
        embed: Embed,
        near_threshold: float,
        min_length: int,
    ) -> tuple[Verification, str]:
        result = verify(document, self.fingerprints(), embed, near_threshold, min_length)
        if not result.accepted or result.fingerprint is None:
            if not self.preview:
                destination = self.root / "quarantine" / safe_id(run_id) / uuid4().hex
                atomic_write(destination / ("source" + suffix), raw)
                write_json(destination / "record.json", {
                    "document": asdict(document), "verification": asdict(result),
                })
            return result, "quarantined"

        doc_id = safe_id(document.doc_id)
        version = safe_id(document.version)
        active = self.manifest["active"]
        versions = self.manifest["versions"].setdefault(doc_id, {})
        previous = active.get(doc_id)
        raw_hash = hashlib.sha256(raw).hexdigest()
        stored = versions.get(version)
        if stored and stored["raw_hash"] != raw_hash:
            raise ValueError(f"revision {doc_id}/{version} already exists with different source bytes")
        serialized = asdict(document) | {"pages": list(document.pages)}
        if previous == version and stored and stored["document"] == serialized:
            return result, "unchanged"

        relative = Path("lake", "archive", doc_id, version)
        if not self.preview:
            atomic_write(self.root / relative / ("source" + suffix), raw)
        stored = {
            "document": serialized,
            "fingerprint": asdict(result.fingerprint),
            "raw_hash": raw_hash,
            "raw_path": (relative / ("source" + suffix)).as_posix(),
        }
        versions[version] = stored
        active[doc_id] = version
        action = "new" if previous is None else "changed"
        self._record(action, doc_id, version)
        return result, action

    def delete(self, doc_id: str) -> None:
        previous = self.manifest["active"].pop(doc_id)
        self._record("deleted", doc_id, previous)

    def restore(self, doc_id: str, version: str) -> None:
        stored = self.manifest["versions"][doc_id][version]
        if not (self.root / stored["raw_path"]).is_file():
            raise FileNotFoundError(stored["raw_path"])
        if self.manifest["active"].get(doc_id) != version:
            self.manifest["active"][doc_id] = version
            self._record("restored", doc_id, version)
